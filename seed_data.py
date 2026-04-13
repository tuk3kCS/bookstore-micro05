"""
BookStore Microservice - Sample Data Seeder
Run this script after all services are up: python seed_data.py
"""
import time
import sys
import json
import os
import urllib.request
import urllib.error

CUSTOMER_URL = "http://localhost:8001"
BOOK_URL = "http://localhost:8002"
CART_URL = "http://localhost:8003"
STAFF_URL = "http://localhost:8004"
MANAGER_URL = "http://localhost:8005"
CATALOG_URL = "http://localhost:8006"
ORDER_URL = "http://localhost:8007"
SHIP_URL = "http://localhost:8008"
PAY_URL = "http://localhost:8009"
REVIEW_URL = "http://localhost:8010"
RECOMMEND_URL = "http://localhost:8011"
CLOTHES_URL = "http://localhost:8012"
BEHAVIOR_URL = "http://localhost:8013"
KB_URL = "http://localhost:8014"
ADVISOR_URL = "http://localhost:8015"


def _http_json(method, url, data=None, timeout=10):
    body = None
    headers = {"Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") if resp.readable() else ""
            if raw:
                try:
                    return resp.status, json.loads(raw)
                except Exception:
                    return resp.status, raw
            return resp.status, {}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
        except Exception:
            raw = ""
        return e.code, raw
    except Exception as e:
        return None, str(e)


def post(url, data):
    status, payload = _http_json("POST", url, data=data, timeout=10)
    if status in (200, 201) and isinstance(payload, dict):
        print(f"  [OK] {url} -> {payload.get('id', '')}")
        return payload
    if status is None:
        print(f"  [ERROR] {url} -> {payload}")
        return None
    text = payload if isinstance(payload, str) else str(payload)
    print(f"  [FAIL] {url} -> {status}: {text[:100]}")
    return None


def wait_for_services():
    print("Waiting for services to be ready...")
    services = [
        ("customer-service", f"{CUSTOMER_URL}/customers/"),
        ("book-service", f"{BOOK_URL}/books/"),
        ("clothes-service", f"{CLOTHES_URL}/products/"),
        ("cart-service", f"{CART_URL}/carts/1/"),
        ("staff-service", f"{STAFF_URL}/staffs/"),
        ("manager-service", f"{MANAGER_URL}/managers/"),
        ("catalog-service", f"{CATALOG_URL}/catalogs/"),
        ("order-service", f"{ORDER_URL}/orders/"),
        ("review-service", f"{REVIEW_URL}/reviews/"),
        ("recommender-service", f"{RECOMMEND_URL}/recommendations/"),
        ("behavior-analytics-service", f"{BEHAVIOR_URL}/health/"),
    ]
    for name, url in services:
        for attempt in range(10):
            try:
                _http_json("GET", url, timeout=3)
                print(f"  {name}: ready")
                break
            except Exception:
                if attempt == 9:
                    print(f"  {name}: NOT READY (skipping)")
                time.sleep(2)


def seed():
    print("\n" + "=" * 50)
    print("  BookStore Sample Data Seeder")
    print("=" * 50)

    wait_for_services()
    if os.environ.get("LLM_API_KEY"):
        print("\n--- Ingesting Knowledge Base (RAG) ---")
        status, payload = _http_json("POST", f"{KB_URL}/kb/ingest/", data={}, timeout=60)
        if status in (200, 201):
            print(f"  [OK] KB ingest -> {payload}")
        else:
            print(f"  [WARN] KB ingest failed -> {status}: {str(payload)[:120]}")
    else:
        print("\n--- Ingesting Knowledge Base (RAG) ---")
        print("  [SKIP] Set LLM_API_KEY env var to enable embeddings + ingest.")

    # ── Catalogs ──
    print("\n--- Creating Catalogs ---")
    catalogs = [
        {"name": "Fiction", "description": "Novels, short stories, and literary fiction"},
        {"name": "Science & Technology", "description": "Computer science, physics, mathematics"},
        {"name": "History", "description": "World history, biographies, and historical events"},
        {"name": "Business", "description": "Management, entrepreneurship, and economics"},
        {"name": "Self-Help", "description": "Personal development and motivation"},
    ]
    for c in catalogs:
        post(f"{CATALOG_URL}/catalogs/", c)

    # ── Books ──
    print("\n--- Creating Books ---")
    # catalog_id: 1=Fiction, 2=Science & Technology, 3=History, 4=Business, 5=Self-Help
    books_data = [
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "price": "12.99", "stock": 50, "catalog_id": 1},
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "price": "14.99", "stock": 35, "catalog_id": 1},
        {"title": "1984", "author": "George Orwell", "price": "11.99", "stock": 60, "catalog_id": 1},
        {"title": "Pride and Prejudice", "author": "Jane Austen", "price": "9.99", "stock": 40, "catalog_id": 1},
        {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "price": "13.50", "stock": 25, "catalog_id": 1},
        {"title": "Clean Code", "author": "Robert C. Martin", "price": "39.99", "stock": 20, "catalog_id": 2},
        {"title": "Design Patterns", "author": "Gang of Four", "price": "49.99", "stock": 15, "catalog_id": 2},
        {"title": "Python Crash Course", "author": "Eric Matthes", "price": "35.99", "stock": 30, "catalog_id": 2},
        {"title": "Microservices Patterns", "author": "Chris Richardson", "price": "44.99", "stock": 18, "catalog_id": 2},
        {"title": "The Pragmatic Programmer", "author": "David Thomas", "price": "42.99", "stock": 22, "catalog_id": 2},
        {"title": "Sapiens", "author": "Yuval Noah Harari", "price": "16.99", "stock": 45, "catalog_id": 3},
        {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "price": "15.99", "stock": 28, "catalog_id": 5},
        {"title": "Atomic Habits", "author": "James Clear", "price": "18.99", "stock": 55, "catalog_id": 5},
        {"title": "The Lean Startup", "author": "Eric Ries", "price": "22.99", "stock": 33, "catalog_id": 4},
        {"title": "Rich Dad Poor Dad", "author": "Robert Kiyosaki", "price": "14.99", "stock": 42, "catalog_id": 4},
    ]
    books = []
    for b in books_data:
        result = post(f"{BOOK_URL}/books/", b)
        if result:
            books.append(result)

    # ── Clothes Products + Variants ──
    print("\n--- Creating Clothes Products + Variants ---")
    clothes_products = [
        {"name": "Classic T-Shirt", "brand": "Urban Basics", "description": "Soft cotton t-shirt for everyday wear", "catalog_id": 4},
        {"name": "Denim Jacket", "brand": "BlueStone", "description": "Timeless denim jacket with a modern fit", "catalog_id": 1},
        {"name": "Running Shorts", "brand": "ActivePro", "description": "Lightweight shorts for training and running", "catalog_id": 2},
    ]
    products = []
    for p in clothes_products:
        result = post(f"{CLOTHES_URL}/products/", p)
        if result:
            products.append(result)

    variants = []
    variants_data = [
        # Product 1: Classic T-Shirt
        {"product": 1, "sku": "TSHIRT-BLK-S", "size": "S", "color": "Black", "price": "9.99", "stock": 40},
        {"product": 1, "sku": "TSHIRT-BLK-M", "size": "M", "color": "Black", "price": "9.99", "stock": 35},
        {"product": 1, "sku": "TSHIRT-WHT-L", "size": "L", "color": "White", "price": "10.99", "stock": 20},
        # Product 2: Denim Jacket
        {"product": 2, "sku": "JACKET-DENIM-M", "size": "M", "color": "Denim", "price": "39.99", "stock": 12},
        {"product": 2, "sku": "JACKET-DENIM-L", "size": "L", "color": "Denim", "price": "39.99", "stock": 8},
        # Product 3: Running Shorts
        {"product": 3, "sku": "SHORTS-GRY-M", "size": "M", "color": "Gray", "price": "14.99", "stock": 25},
        {"product": 3, "sku": "SHORTS-BLU-L", "size": "L", "color": "Blue", "price": "14.99", "stock": 18},
    ]
    for v in variants_data:
        result = post(f"{CLOTHES_URL}/variants/", v)
        if result:
            variants.append(result)

    # ── Customers (auto-creates carts) ──
    print("\n--- Creating Customers (+ auto cart) ---")
    customers_data = [
        {"name": "Nguyen Van An", "email": "an.nguyen@email.com", "password": "123456"},
        {"name": "Tran Thi Binh", "email": "binh.tran@email.com", "password": "123456"},
        {"name": "Le Hoang Cuong", "email": "cuong.le@email.com", "password": "123456"},
        {"name": "Pham Minh Duc", "email": "duc.pham@email.com", "password": "123456"},
        {"name": "Vo Thanh Em", "email": "em.vo@email.com", "password": "123456"},
        {"name": "Hoang Thi Phuong", "email": "phuong.hoang@email.com", "password": "123456"},
        {"name": "Dang Quoc Gia", "email": "gia.dang@email.com", "password": "123456"},
        {"name": "Bui Van Hung", "email": "hung.bui@email.com", "password": "123456"},
    ]
    customers = []
    for c in customers_data:
        result = post(f"{CUSTOMER_URL}/customers/", c)
        if result:
            customers.append(result)

    # ── Behavior events (demo) ──
    print("\n--- Sending Demo Behavior Events ---")
    demo_events = [
        {"customer_id": 1, "event_type": "page_view", "page": "/", "metadata": {"page": "home"}},
        {"customer_id": 1, "event_type": "view_item", "item_type": "book", "item_id": 6, "page": "/books/6/"},
        {"customer_id": 1, "event_type": "add_to_cart", "item_type": "book", "item_id": 6, "page": "/books/6/", "metadata": {"quantity": 1}},
        {"customer_id": 2, "event_type": "view_item", "item_type": "clothes_variant", "item_id": 4, "page": "/clothes/2/"},
        {"customer_id": 2, "event_type": "add_to_cart", "item_type": "clothes_variant", "item_id": 4, "page": "/clothes/2/", "metadata": {"quantity": 1}},
    ]
    for ev in demo_events:
        post(f"{BEHAVIOR_URL}/events/", ev)

    # ── Advisor chat (smoke) ──
    print("\n--- Advisor Chat Smoke Test ---")
    if os.environ.get("LLM_API_KEY"):
        msg = {"customer_id": 1, "message": "Tôi muốn biết các phương thức thanh toán hỗ trợ?"}
        status, payload = _http_json("POST", f"{ADVISOR_URL}/advisor/chat/", data=msg, timeout=90)
        if status in (200, 201) and isinstance(payload, dict):
            ans = payload.get("answer", "")
            print(f"  [OK] advisor -> {ans[:140]}")
        else:
            print(f"  [WARN] advisor chat failed -> {status}: {str(payload)[:140]}")
    else:
        print("  [SKIP] Set LLM_API_KEY env var to enable chat.")

    # Ensure carts exist for demo customers (best-effort).
    print("\n--- Ensuring Carts Exist ---")
    for cid in range(1, len(customers_data) + 1):
        status, _ = _http_json("GET", f"{CART_URL}/carts/info/{cid}/", timeout=5)
        if status != 200:
            post(f"{CART_URL}/carts/", {"customer_id": cid})

    # ── Staff ──
    print("\n--- Creating Staff ---")
    staff_data = [
        {"name": "Nguyen Thi Lan", "email": "lan.nguyen@bookstore.com", "position": "Librarian", "password": "123456"},
        {"name": "Tran Van Minh", "email": "minh.tran@bookstore.com", "position": "Cashier", "password": "123456"},
        {"name": "Le Thi Ngoc", "email": "ngoc.le@bookstore.com", "position": "Inventory Manager", "password": "123456"},
        {"name": "Pham Quoc Bao", "email": "bao.pham@bookstore.com", "position": "Sales Associate", "password": "123456"},
        {"name": "Vo Hoang Nam", "email": "nam.vo@bookstore.com", "position": "IT Support", "password": "123456"},
    ]
    for s in staff_data:
        post(f"{STAFF_URL}/staffs/", s)

    # ── Managers ──
    print("\n--- Creating Managers ---")
    managers_data = [
        {"name": "Dr. Tran Dinh Que", "email": "que.tran@bookstore.com", "department": "Operations"},
        {"name": "Nguyen Thanh Son", "email": "son.nguyen@bookstore.com", "department": "Sales"},
        {"name": "Le Minh Tuan", "email": "tuan.le@bookstore.com", "department": "Technology"},
    ]
    for m in managers_data:
        post(f"{MANAGER_URL}/managers/", m)

    # ── Add Cart Items ──
    print("\n--- Adding Items to Carts ---")
    if books and customers:
        cart_items = [
            {"cart": 1, "book_id": 1, "quantity": 2},
            {"cart": 1, "book_id": 6, "quantity": 1},
            {"cart": 1, "book_id": 13, "quantity": 1},
            {"cart": 2, "book_id": 3, "quantity": 1},
            {"cart": 2, "book_id": 9, "quantity": 1},
            {"cart": 3, "book_id": 8, "quantity": 2},
            {"cart": 3, "book_id": 10, "quantity": 1},
            {"cart": 4, "book_id": 11, "quantity": 1},
            {"cart": 4, "book_id": 12, "quantity": 1},
            {"cart": 5, "book_id": 14, "quantity": 3},
            # Clothes variants
            {"cart": 1, "item_type": "clothes", "item_id": 1, "quantity": 1},
            {"cart": 2, "item_type": "clothes", "item_id": 4, "quantity": 1},
            {"cart": 3, "item_type": "clothes", "item_id": 6, "quantity": 2},
        ]
        for item in cart_items:
            post(f"{CART_URL}/cart-items/", item)

    # ── Orders (auto-creates payments and shipments) ──
    print("\n--- Creating Orders (+ auto payment & shipment) ---")
    orders_data = [
        {
            "customer_id": 1,
            "items": [
                {"book_id": 1, "quantity": 1, "price": "12.99"},
                {"book_id": 6, "quantity": 1, "price": "39.99"},
                {"item_type": "clothes", "item_id": 1, "quantity": 1, "price": "9.99"},
            ],
            "payment_method": "credit_card",
            "shipping_address": "123 Le Loi, District 1, Ho Chi Minh City",
        },
        {
            "customer_id": 2,
            "items": [
                {"book_id": 3, "quantity": 2, "price": "11.99"},
                {"book_id": 13, "quantity": 1, "price": "18.99"},
                {"item_type": "clothes", "item_id": 4, "quantity": 1, "price": "39.99"},
            ],
            "payment_method": "bank_transfer",
            "shipping_address": "456 Tran Hung Dao, Hoan Kiem, Hanoi",
        },
        {
            "customer_id": 3,
            "items": [
                {"book_id": 8, "quantity": 1, "price": "35.99"},
                {"book_id": 9, "quantity": 1, "price": "44.99"},
                {"book_id": 10, "quantity": 1, "price": "42.99"},
                {"item_type": "clothes", "item_id": 6, "quantity": 1, "price": "14.99"},
            ],
            "payment_method": "credit_card",
            "shipping_address": "789 Nguyen Hue, Hai Chau, Da Nang",
        },
        {
            "customer_id": 4,
            "items": [
                {"book_id": 11, "quantity": 1, "price": "16.99"},
            ],
            "payment_method": "cash",
            "shipping_address": "321 Hung Vuong, Ninh Kieu, Can Tho",
        },
        {
            "customer_id": 1,
            "items": [
                {"book_id": 14, "quantity": 1, "price": "22.99"},
                {"book_id": 15, "quantity": 1, "price": "14.99"},
            ],
            "payment_method": "debit_card",
            "shipping_address": "123 Le Loi, District 1, Ho Chi Minh City",
        },
        {
            "customer_id": 5,
            "items": [
                {"book_id": 2, "quantity": 1, "price": "14.99"},
                {"book_id": 4, "quantity": 1, "price": "9.99"},
                {"book_id": 5, "quantity": 1, "price": "13.50"},
            ],
            "payment_method": "credit_card",
            "shipping_address": "55 Phan Chu Trinh, Hue City",
        },
    ]
    for o in orders_data:
        post(f"{ORDER_URL}/orders/", o)

    # ── Reviews ──
    print("\n--- Creating Reviews ---")
    reviews_data = [
        {"customer_id": 1, "book_id": 1, "rating": 5, "comment": "A masterpiece of American literature. Fitzgerald's prose is beautiful."},
        {"customer_id": 1, "book_id": 6, "rating": 5, "comment": "Essential reading for every developer. Changed how I write code."},
        {"customer_id": 2, "book_id": 3, "rating": 4, "comment": "Chilling and prophetic. More relevant today than ever."},
        {"customer_id": 2, "book_id": 13, "rating": 5, "comment": "Practical advice that actually works. Highly recommend!"},
        {"customer_id": 3, "book_id": 8, "rating": 4, "comment": "Great for beginners. Clear explanations and good projects."},
        {"customer_id": 3, "book_id": 9, "rating": 5, "comment": "The definitive guide to microservices architecture. A must-read."},
        {"customer_id": 3, "book_id": 10, "rating": 4, "comment": "Timeless advice for software developers. Still very relevant."},
        {"customer_id": 4, "book_id": 11, "rating": 5, "comment": "Fascinating journey through human history. Couldn't put it down."},
        {"customer_id": 5, "book_id": 2, "rating": 5, "comment": "A powerful story about justice and compassion. Truly moving."},
        {"customer_id": 5, "book_id": 4, "rating": 4, "comment": "Witty and charming. Austen at her finest."},
        {"customer_id": 6, "book_id": 12, "rating": 4, "comment": "Eye-opening insights into how we think and make decisions."},
        {"customer_id": 6, "book_id": 14, "rating": 3, "comment": "Some good ideas but a bit repetitive in parts."},
        {"customer_id": 7, "book_id": 7, "rating": 5, "comment": "Classic software engineering reference. Every pattern is well explained."},
        {"customer_id": 7, "book_id": 15, "rating": 4, "comment": "Simple financial advice that everyone should hear early in life."},
        {"customer_id": 8, "book_id": 5, "rating": 3, "comment": "Interesting character study but not for everyone."},
        # Clothes variant reviews
        {"customer_id": 1, "item_type": "clothes", "item_id": 1, "rating": 5, "comment": "Great fit and very comfortable."},
        {"customer_id": 2, "item_type": "clothes", "item_id": 4, "rating": 4, "comment": "Jacket looks awesome, quality is solid."},
        {"customer_id": 3, "item_type": "clothes", "item_id": 6, "rating": 4, "comment": "Perfect for running. Light and breathable."},
    ]
    for r in reviews_data:
        post(f"{REVIEW_URL}/reviews/", r)

    # ── Recommendations ──
    print("\n--- Creating Recommendations ---")
    recommendations_data = [
        {"customer_id": 1, "book_id": 9, "score": 95.5, "reason": "Based on your interest in Clean Code"},
        {"customer_id": 1, "book_id": 10, "score": 88.0, "reason": "Popular among developers who read Clean Code"},
        {"customer_id": 1, "book_id": 7, "score": 82.3, "reason": "Complements your software engineering reading"},
        {"customer_id": 1, "item_type": "clothes", "item_id": 4, "score": 78.5, "reason": "Popular pick in your favorite categories"},
        {"customer_id": 2, "book_id": 11, "score": 91.0, "reason": "Readers who liked 1984 also enjoyed Sapiens"},
        {"customer_id": 2, "book_id": 12, "score": 85.5, "reason": "Popular in the non-fiction category"},
        {"customer_id": 2, "item_type": "clothes", "item_id": 1, "score": 72.0, "reason": "Trending apparel you might like"},
        {"customer_id": 3, "book_id": 6, "score": 93.2, "reason": "Essential companion to your programming books"},
        {"customer_id": 3, "book_id": 7, "score": 89.7, "reason": "Next level software design patterns"},
        {"customer_id": 3, "item_type": "clothes", "item_id": 6, "score": 70.0, "reason": "Based on your active lifestyle picks"},
        {"customer_id": 4, "book_id": 12, "score": 87.0, "reason": "Similar to Sapiens in scope and depth"},
        {"customer_id": 4, "book_id": 13, "score": 79.5, "reason": "Trending book in self-improvement"},
        {"customer_id": 5, "book_id": 1, "score": 90.0, "reason": "Classic literature matching your taste"},
        {"customer_id": 5, "book_id": 3, "score": 86.8, "reason": "Readers of To Kill a Mockingbird also loved 1984"},
        {"customer_id": 6, "book_id": 13, "score": 88.5, "reason": "Highly rated in behavior & psychology"},
        {"customer_id": 7, "book_id": 9, "score": 94.0, "reason": "Perfect for your software architecture interests"},
        {"customer_id": 8, "book_id": 1, "score": 75.0, "reason": "Top classic fiction recommendation"},
        {"customer_id": 8, "book_id": 2, "score": 82.0, "reason": "Award-winning literature you might enjoy"},
    ]
    for rec in recommendations_data:
        post(f"{RECOMMEND_URL}/recommendations/", rec)

    print("\n" + "=" * 50)
    print("  Seeding complete!")
    print("=" * 50)
    print("\nSummary:")
    print(f"  Catalogs:        5")
    print(f"  Books:           15")
    print(f"  Clothes Products: 3")
    print(f"  Clothes Variants: 7")
    print(f"  Customers:       8  (+ 8 carts auto-created)")
    print(f"  Staff:           5")
    print(f"  Managers:        3")
    print(f"  Cart Items:      13")
    print(f"  Orders:          6  (+ 6 payments & 6 shipments auto-created)")
    print(f"  Reviews:         18")
    print(f"  Recommendations: 18")
    print(f"\nCustomer Portal:  http://localhost:8000/")
    print(f"Admin Dashboard:  http://localhost:8000/dashboard/")
    print(f"\nAll demo accounts use password: 123456")
    print(f"Customer login example: an.nguyen@email.com / 123456")
    print(f"Staff login example:    lan.nguyen@bookstore.com / 123456")


if __name__ == "__main__":
    seed()
