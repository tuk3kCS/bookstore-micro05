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
CLOTHES_SERVICE_URL = "http://clothes-service:8000"
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
    clothes_products = _fetch(f"{CLOTHES_SERVICE_URL}/products/")
    clothes_variants = _fetch(f"{CLOTHES_SERVICE_URL}/variants/")
    orders = _fetch(f"{ORDER_SERVICE_URL}/orders/")
    all_reviews = _fetch(f"{REVIEW_SERVICE_URL}/reviews/")

    if not books and not clothes_variants:
        return []

    products_map = {p["id"]: p for p in clothes_products}
    books_map = {b["id"]: b for b in books}
    variants_map = {v["id"]: v for v in clothes_variants}

    # Candidate universe (item_type, item_id)
    all_items = set()
    for bid in books_map.keys():
        all_items.add(("book", bid))
    for vid, v in variants_map.items():
        all_items.add(("clothes", vid))

    # ── Gather customer interaction data ────────────────────────────
    customer_orders = [o for o in orders if o.get("customer_id") == customer_id]
    customer_reviews = [r for r in all_reviews if r.get("customer_id") == customer_id]

    purchased_items = set()
    for order in customer_orders:
        for item in order.get("items", []):
            itype = item.get("item_type") or ("book" if item.get("book_id") is not None else "book")
            iid = item.get("item_id") or item.get("book_id")
            if iid is not None:
                purchased_items.add((itype, int(iid)))

    reviewed_items = set()
    for rv in customer_reviews:
        itype = rv.get("item_type") or ("book" if rv.get("book_id") is not None else "book")
        iid = rv.get("item_id") or rv.get("book_id")
        if iid is not None:
            reviewed_items.add((itype, int(iid)))

    interacted_items = purchased_items | reviewed_items
    candidate_items = all_items - interacted_items

    if not candidate_items:
        candidate_items = all_items

    # ── 1. Content-based: category preference ───────────────────────
    cat_scores = defaultdict(float)
    cat_counts = defaultdict(int)

    def _catalog_id_for_item(item_type: str, item_id: int):
        if item_type == "book":
            b = books_map.get(item_id)
            return b.get("catalog_id") if b else None
        if item_type == "clothes":
            v = variants_map.get(item_id)
            if not v:
                return None
            p = products_map.get(v.get("product"))
            return p.get("catalog_id") if p else None
        return None

    for itype, iid in purchased_items:
        cid = _catalog_id_for_item(itype, iid)
        if cid:
            cat_scores[cid] += 1.0
            cat_counts[cid] += 1

    for rv in customer_reviews:
        itype = rv.get("item_type") or ("book" if rv.get("book_id") is not None else "book")
        iid = rv.get("item_id") or rv.get("book_id")
        if iid is None:
            continue
        cid = _catalog_id_for_item(itype, int(iid))
        if cid:
            rating = rv.get("rating", 3)
            cat_scores[cid] += rating / 5.0
            cat_counts[cid] += 1

    max_cat_score = max(cat_scores.values()) if cat_scores else 1

    content_scores = {}
    for itype, iid in candidate_items:
        cid = _catalog_id_for_item(itype, iid)
        if cid and cid in cat_scores:
            content_scores[(itype, iid)] = (cat_scores[cid] / max_cat_score) * 100
        else:
            content_scores[(itype, iid)] = 10.0

    # ── 2. Collaborative filtering: user-user similarity ────────────
    user_ratings = defaultdict(dict)  # user_id -> {(type,id): rating}
    for rv in all_reviews:
        itype = rv.get("item_type") or ("book" if rv.get("book_id") is not None else "book")
        iid = rv.get("item_id") or rv.get("book_id")
        if iid is None:
            continue
        user_ratings[rv["customer_id"]][(itype, int(iid))] = rv.get("rating", 3)

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
            for key, rating in user_ratings[other_uid].items():
                if key in candidate_items:
                    collaborative_scores[key] += sim * rating

        max_collab = max(collaborative_scores.values()) if collaborative_scores else 1
        for key in collaborative_scores:
            collaborative_scores[key] = (collaborative_scores[key] / max_collab) * 100

    for key in candidate_items:
        collaborative_scores.setdefault(key, 5.0)

    # ── 3. Popularity scoring ───────────────────────────────────────
    item_ratings = defaultdict(list)
    for rv in all_reviews:
        itype = rv.get("item_type") or ("book" if rv.get("book_id") is not None else "book")
        iid = rv.get("item_id") or rv.get("book_id")
        if iid is None:
            continue
        item_ratings[(itype, int(iid))].append(rv.get("rating", 3))

    popularity_scores = {}
    for key in candidate_items:
        ratings = item_ratings.get(key, [])
        if ratings:
            avg = sum(ratings) / len(ratings)
            count_factor = min(len(ratings) / 5.0, 1.0)  # up to 5 reviews = full weight
            popularity_scores[key] = (avg / 5.0) * count_factor * 100
        else:
            popularity_scores[key] = 15.0

    # ── 4. Recency / stock bonus ────────────────────────────────────
    recency_scores = {}
    max_numeric_id = max((iid for _, iid in candidate_items), default=1)

    def _stock_for_item(item_type: str, item_id: int) -> int:
        if item_type == "book":
            b = books_map.get(item_id)
            return int(b.get("stock", 0)) if b else 0
        if item_type == "clothes":
            v = variants_map.get(item_id)
            return int(v.get("stock", 0)) if v else 0
        return 0

    for itype, iid in candidate_items:
        id_score = (iid / max_numeric_id) * 60
        stock_bonus = 40 if _stock_for_item(itype, iid) > 0 else 0
        recency_scores[(itype, iid)] = id_score + stock_bonus

    # ── Blend scores ────────────────────────────────────────────────
    final_scores = {}
    for key in candidate_items:
        score = (
            WEIGHTS["content"] * content_scores.get(key, 0)
            + WEIGHTS["collaborative"] * collaborative_scores.get(key, 0)
            + WEIGHTS["popularity"] * popularity_scores.get(key, 0)
            + WEIGHTS["recency"] * recency_scores.get(key, 0)
        )
        final_scores[key] = round(min(score, 100), 1)

    sorted_recs = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top = sorted_recs[:MAX_RECOMMENDATIONS]

    # ── Build reason strings ────────────────────────────────────────
    results = []
    for (itype, iid), score in top:
        if score < 5:
            continue
        reasons = []

        cs = content_scores.get((itype, iid), 0)
        cls = collaborative_scores.get((itype, iid), 0)
        ps = popularity_scores.get((itype, iid), 0)

        if cs > 50:
            reasons.append("Matches your preferred categories")
        if cls > 50:
            reasons.append("Liked by readers with similar taste")
        if ps > 60:
            avg_r = item_ratings.get((itype, iid), [])
            if avg_r:
                reasons.append(f"Highly rated ({sum(avg_r)/len(avg_r):.1f}/5 avg)")
        if not reasons:
            if _stock_for_item(itype, iid) > 0:
                reasons.append("Popular pick you haven't explored yet")
            else:
                reasons.append("Trending title in our catalog")

        results.append({
            "customer_id": customer_id,
            "item_type": itype,
            "item_id": iid,
            "score": score,
            "reason": " · ".join(reasons),
        })

    return results
