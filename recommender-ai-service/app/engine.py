"""
AI Recommendation Engine

Uses a hybrid approach combining:
  1. Content-based filtering  (category preferences from orders/reviews)
  2. Collaborative filtering  (user-user similarity via review ratings)
  3. Popularity scoring       (average rating + review count)
  4. Stock awareness          (penalise out-of-stock books)

Each factor produces a normalised 0-100 score. The final score is a
weighted blend, and a human-readable reason string is generated.
"""

import math
from collections import defaultdict

import numpy as np
import requests

BOOK_SERVICE_URL = "http://book-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
REVIEW_SERVICE_URL = "http://comment-rate-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"

WEIGHTS = {
    "content": 0.35,
    "collaborative": 0.30,
    "popularity": 0.20,
    "recency": 0.15,
}

MAX_RECOMMENDATIONS = 10


def _fetch(url):
    try:
        r = requests.get(url, timeout=8)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def generate_recommendations(customer_id: int) -> list[dict]:
    books = _fetch(f"{BOOK_SERVICE_URL}/books/")
    orders = _fetch(f"{ORDER_SERVICE_URL}/orders/")
    all_reviews = _fetch(f"{REVIEW_SERVICE_URL}/reviews/")

    if not books:
        return []

    books_map = {b["id"]: b for b in books}
    book_ids = set(books_map.keys())

    # ── Gather customer interaction data ────────────────────────────
    customer_orders = [o for o in orders if o.get("customer_id") == customer_id]
    customer_reviews = [r for r in all_reviews if r.get("customer_id") == customer_id]

    purchased_book_ids = set()
    for order in customer_orders:
        for item in order.get("items", []):
            purchased_book_ids.add(item.get("book_id"))

    reviewed_book_ids = {r["book_id"] for r in customer_reviews}
    interacted_book_ids = purchased_book_ids | reviewed_book_ids
    candidate_ids = book_ids - interacted_book_ids

    if not candidate_ids:
        candidate_ids = book_ids

    # ── 1. Content-based: category preference ───────────────────────
    cat_scores = defaultdict(float)
    cat_counts = defaultdict(int)

    for bid in purchased_book_ids:
        book = books_map.get(bid)
        if book and book.get("catalog_id"):
            cat_scores[book["catalog_id"]] += 1.0
            cat_counts[book["catalog_id"]] += 1

    for rv in customer_reviews:
        book = books_map.get(rv["book_id"])
        if book and book.get("catalog_id"):
            rating = rv.get("rating", 3)
            cat_scores[book["catalog_id"]] += rating / 5.0
            cat_counts[book["catalog_id"]] += 1

    max_cat_score = max(cat_scores.values()) if cat_scores else 1

    content_scores = {}
    for bid in candidate_ids:
        book = books_map.get(bid)
        cid = book.get("catalog_id") if book else None
        if cid and cid in cat_scores:
            content_scores[bid] = (cat_scores[cid] / max_cat_score) * 100
        else:
            content_scores[bid] = 10.0  # small baseline

    # ── 2. Collaborative filtering: user-user similarity ────────────
    user_ratings = defaultdict(dict)  # user_id -> {book_id: rating}
    for rv in all_reviews:
        user_ratings[rv["customer_id"]][rv["book_id"]] = rv.get("rating", 3)

    target_ratings = user_ratings.get(customer_id, {})

    collaborative_scores = defaultdict(float)
    if target_ratings:
        similarities = {}
        for other_uid, other_ratings in user_ratings.items():
            if other_uid == customer_id:
                continue
            common = set(target_ratings.keys()) & set(other_ratings.keys())
            if not common:
                continue
            vec_a = np.array([target_ratings[b] for b in common], dtype=float)
            vec_b = np.array([other_ratings[b] for b in common], dtype=float)
            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)
            if norm_a == 0 or norm_b == 0:
                continue
            cosine_sim = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
            if cosine_sim > 0:
                similarities[other_uid] = cosine_sim

        for other_uid, sim in similarities.items():
            for bid, rating in user_ratings[other_uid].items():
                if bid in candidate_ids:
                    collaborative_scores[bid] += sim * rating

        max_collab = max(collaborative_scores.values()) if collaborative_scores else 1
        for bid in collaborative_scores:
            collaborative_scores[bid] = (collaborative_scores[bid] / max_collab) * 100

    for bid in candidate_ids:
        collaborative_scores.setdefault(bid, 5.0)

    # ── 3. Popularity scoring ───────────────────────────────────────
    book_ratings = defaultdict(list)
    for rv in all_reviews:
        book_ratings[rv["book_id"]].append(rv.get("rating", 3))

    popularity_scores = {}
    for bid in candidate_ids:
        ratings = book_ratings.get(bid, [])
        if ratings:
            avg = sum(ratings) / len(ratings)
            count_factor = min(len(ratings) / 5.0, 1.0)  # up to 5 reviews = full weight
            popularity_scores[bid] = (avg / 5.0) * count_factor * 100
        else:
            popularity_scores[bid] = 15.0  # baseline for unreviewed

    # ── 4. Recency / stock bonus ────────────────────────────────────
    recency_scores = {}
    max_id = max(candidate_ids) if candidate_ids else 1
    for bid in candidate_ids:
        book = books_map.get(bid)
        id_score = (bid / max_id) * 60
        stock_bonus = 40 if book and book.get("stock", 0) > 0 else 0
        recency_scores[bid] = id_score + stock_bonus

    # ── Blend scores ────────────────────────────────────────────────
    final_scores = {}
    for bid in candidate_ids:
        score = (
            WEIGHTS["content"] * content_scores.get(bid, 0)
            + WEIGHTS["collaborative"] * collaborative_scores.get(bid, 0)
            + WEIGHTS["popularity"] * popularity_scores.get(bid, 0)
            + WEIGHTS["recency"] * recency_scores.get(bid, 0)
        )
        final_scores[bid] = round(min(score, 100), 1)

    sorted_recs = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top = sorted_recs[:MAX_RECOMMENDATIONS]

    # ── Build reason strings ────────────────────────────────────────
    results = []
    for bid, score in top:
        if score < 5:
            continue
        book = books_map.get(bid, {})
        reasons = []

        cs = content_scores.get(bid, 0)
        cls = collaborative_scores.get(bid, 0)
        ps = popularity_scores.get(bid, 0)

        if cs > 50:
            cat_id = book.get("catalog_id")
            reasons.append("Matches your preferred categories")
        if cls > 50:
            reasons.append("Liked by readers with similar taste")
        if ps > 60:
            avg_r = book_ratings.get(bid, [])
            if avg_r:
                reasons.append(f"Highly rated ({sum(avg_r)/len(avg_r):.1f}/5 avg)")
        if not reasons:
            if book.get("stock", 0) > 0:
                reasons.append("Popular pick you haven't explored yet")
            else:
                reasons.append("Trending title in our catalog")

        results.append({
            "customer_id": customer_id,
            "book_id": bid,
            "score": score,
            "reason": " · ".join(reasons),
        })

    return results
