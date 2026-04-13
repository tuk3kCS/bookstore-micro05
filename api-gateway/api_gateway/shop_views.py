from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import threading
import uuid
import requests as http_requests

BOOK_SERVICE_URL = "http://book-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
CLOTHES_SERVICE_URL = "http://clothes-service:8000"
BEHAVIOR_SERVICE_URL = "http://behavior-analytics-service:8000"
ADVISOR_SERVICE_URL = "http://chat-advisor-service:8000"


def _safe_get(url):
    try:
        r = http_requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def _safe_post(url, data):
    try:
        return http_requests.post(url, json=data, timeout=5)
    except Exception:
        return None


def _safe_put(url, data):
    try:
        return http_requests.put(url, json=data, timeout=5)
    except Exception:
        return None


def _ensure_session_id(request):
    sid = request.session.get("behavior_session_id")
    if not sid:
        sid = f"sess_{uuid.uuid4().hex}"
        request.session["behavior_session_id"] = sid
    return sid


def _emit_event_async(request, event_type, item_type="", item_id=None, metadata=None):
    """
    Best-effort, non-blocking event tracking.
    Never raises; failures are ignored.
    """
    try:
        customer_id = request.session.get("customer_id")
        payload = {
            "customer_id": customer_id,
            "session_id": _ensure_session_id(request),
            "correlation_id": request.META.get("HTTP_X_REQUEST_ID", ""),
            "event_type": event_type,
            "page": request.path,
            "referrer": request.META.get("HTTP_REFERER", "")[:255],
            "item_type": item_type or "",
            "item_id": item_id,
            "metadata": metadata or {},
            "user_agent": (request.META.get("HTTP_USER_AGENT", "") or "")[:255],
        }
        # Best effort: IP may be missing/invalid in dev; omit if empty.
        ip = request.META.get("REMOTE_ADDR", "")
        if ip:
            payload["ip"] = ip

        def _send():
            try:
                http_requests.post(f"{BEHAVIOR_SERVICE_URL}/events/", json=payload, timeout=1.5)
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()
    except Exception:
        pass


def _get_customer(request):
    cid = request.session.get("customer_id")
    if not cid:
        return None
    try:
        customers = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
        for c in customers:
            if c["id"] == cid:
                return c
    except Exception:
        pass
    return None


def _require_login(request):
    if not request.session.get("customer_id"):
        messages.warning(request, "Please sign in first.")
        return redirect("shop_login")
    return None


def _get_cart_id(customer_id):
    """Get the Cart primary key for a customer via the cart-info endpoint."""
    try:
        r = http_requests.get(f"{CART_SERVICE_URL}/carts/info/{customer_id}/", timeout=5)
        if r.status_code == 200:
            return r.json().get("id")
    except Exception:
        pass
    return None


def _get_item_key(item_type, item_id, fallback_book_id=None):
    t = item_type or ("book" if fallback_book_id is not None else "book")
    i = item_id if item_id is not None else fallback_book_id
    try:
        return t, int(i) if i is not None else None
    except Exception:
        return t, None


def _load_clothes_data():
    products = _safe_get(f"{CLOTHES_SERVICE_URL}/products/")
    variants = _safe_get(f"{CLOTHES_SERVICE_URL}/variants/")
    products_map = {p["id"]: p for p in products}
    variants_map = {v["id"]: v for v in variants}
    return products, variants, products_map, variants_map


def _enrich_recommendations(recs, books_map, catalogs_map):
    _, _, products_map, variants_map = _load_clothes_data()
    enriched = []
    for rec in recs or []:
        itype, iid = _get_item_key(rec.get("item_type"), rec.get("item_id"), rec.get("book_id"))
        if iid is None:
            continue
        rec["item_type"] = itype
        rec["item_id"] = iid
        if itype == "book":
            book = books_map.get(iid)
            if not book:
                continue
            rec["item_title"] = book.get("title", "Book")
            rec["item_subtitle"] = f"by {book.get('author', 'Unknown')}"
            rec["item_price"] = book.get("price", "")
            rec["item_stock"] = book.get("stock", 0)
            rec["catalog_name"] = catalogs_map.get(book.get("catalog_id"), "")
            rec["item_url"] = f"/books/{iid}/"
            rec["item_icon"] = "bi-journal-richtext"
        else:
            variant = variants_map.get(iid)
            if not variant:
                continue
            product = products_map.get(variant.get("product"))
            if not product:
                continue
            title = product.get("name", "Clothes")
            size = variant.get("size", "")
            color = variant.get("color", "")
            desc = " · ".join([x for x in [size, color] if x])
            rec["item_title"] = title
            rec["item_subtitle"] = desc or product.get("brand", "")
            rec["item_price"] = variant.get("price", "")
            rec["item_stock"] = variant.get("stock", 0)
            rec["catalog_name"] = catalogs_map.get(product.get("catalog_id"), "")
            rec["item_url"] = f"/clothes/{product.get('id')}/"
            rec["item_icon"] = "bi-bag"
        enriched.append(rec)
    enriched.sort(key=lambda r: r.get("score", 0), reverse=True)
    return enriched


# ───────── Home ─────────

def shop_home(request):
    customer = _get_customer(request)
    _emit_event_async(request, "page_view", metadata={"page": "home"})
    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    books_map = {b["id"]: b for b in books}
    catalogs_map = {c["id"]: c["name"] for c in catalogs}

    catalog_counts = {}
    for b in books:
        cid = b.get("catalog_id")
        if cid:
            catalog_counts[cid] = catalog_counts.get(cid, 0) + 1
    for cat in catalogs:
        cat["book_count"] = catalog_counts.get(cat["id"], 0)

    recommendations = []
    if customer:
        cid = customer["id"]
        recommendations = _safe_get(f"{RECOMMENDER_SERVICE_URL}/recommendations/{cid}/")
        if not recommendations:
            try:
                r = http_requests.post(
                    f"{RECOMMENDER_SERVICE_URL}/recommendations/generate/{cid}/",
                    json={}, timeout=15,
                )
                if r and r.status_code == 201:
                    recommendations = r.json()
            except Exception:
                pass
        recommendations = _enrich_recommendations(recommendations, books_map, catalogs_map)

    return render(request, "shop/home.html", {
        "customer": customer,
        "featured_books": books[:8],
        "catalogs": catalogs,
        "recommendations": recommendations[:6],
    })


# ───────── Login / Register / Logout ─────────

def shop_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        if email and password:
            r = _safe_post(f"{CUSTOMER_SERVICE_URL}/customers/login/", {"email": email, "password": password})
            if r and r.status_code == 200:
                customer = r.json()
                request.session["customer_id"] = customer["id"]
                request.session["customer_name"] = customer["name"]
                _emit_event_async(request, "login", metadata={"email": email})
                messages.success(request, f"Welcome back, {customer['name']}!")
                return redirect("shop_home")
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please enter both email and password.")
    else:
        _emit_event_async(request, "page_view", metadata={"page": "login"})
    return render(request, "shop/login.html", {"customer": None})


def shop_register(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        if not name or not email or not password:
            messages.error(request, "All fields are required.")
        elif password != password2:
            messages.error(request, "Passwords do not match.")
        else:
            data = {"name": name, "email": email, "password": password}
            r = _safe_post(f"{CUSTOMER_SERVICE_URL}/customers/", data)
            if r and r.status_code in (200, 201):
                new_customer = r.json()
                request.session["customer_id"] = new_customer["id"]
                request.session["customer_name"] = new_customer.get("name", name)
                _emit_event_async(request, "register", metadata={"email": email})
                messages.success(request, f"Welcome, {name}! Your account and cart have been created.")
                return redirect("shop_home")
            else:
                messages.error(request, "Registration failed. Email may already be in use.")
    else:
        _emit_event_async(request, "page_view", metadata={"page": "register"})
    return render(request, "shop/login.html", {"customer": None, "show_register": True})


def shop_logout(request):
    request.session.flush()
    messages.info(request, "You have been signed out.")
    return redirect("shop_home")


# ───────── Browse Books ─────────

def shop_books(request):
    customer = _get_customer(request)
    _emit_event_async(request, "page_view", metadata={"page": "books", "q": request.GET.get("q", ""), "catalog": request.GET.get("catalog", "")})
    all_books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    catalogs_map = {c["id"]: c["name"] for c in catalogs}

    q = request.GET.get("q", "").strip()
    catalog_filter = request.GET.get("catalog", "")
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    in_stock = request.GET.get("in_stock", "")
    sort_by = request.GET.get("sort", "")

    books = all_books

    if q:
        ql = q.lower()
        books = [b for b in books if ql in b["title"].lower() or ql in b["author"].lower()]

    if catalog_filter:
        try:
            cid = int(catalog_filter)
            books = [b for b in books if b.get("catalog_id") == cid]
        except (ValueError, TypeError):
            pass

    if price_min:
        try:
            pmin = float(price_min)
            books = [b for b in books if float(b["price"]) >= pmin]
        except (ValueError, TypeError):
            pass

    if price_max:
        try:
            pmax = float(price_max)
            books = [b for b in books if float(b["price"]) <= pmax]
        except (ValueError, TypeError):
            pass

    if in_stock == "1":
        books = [b for b in books if b.get("stock", 0) > 0]

    if sort_by == "price_asc":
        books.sort(key=lambda b: float(b["price"]))
    elif sort_by == "price_desc":
        books.sort(key=lambda b: float(b["price"]), reverse=True)
    elif sort_by == "title":
        books.sort(key=lambda b: b["title"].lower())
    elif sort_by == "newest":
        books.sort(key=lambda b: b.get("id", 0), reverse=True)

    for b in books:
        b["catalog_name"] = catalogs_map.get(b.get("catalog_id"), "")

    catalog_counts = {}
    for b in all_books:
        cid = b.get("catalog_id")
        if cid:
            catalog_counts[cid] = catalog_counts.get(cid, 0) + 1

    return render(request, "shop/books.html", {
        "customer": customer,
        "books": books,
        "total_count": len(all_books),
        "catalogs": catalogs,
        "catalog_counts": catalog_counts,
        "q": q,
        "catalog_filter": catalog_filter,
        "price_min": price_min,
        "price_max": price_max,
        "in_stock": in_stock,
        "sort_by": sort_by,
    })


# ───────── Book Detail ─────────

def shop_book_detail(request, pk):
    customer = _get_customer(request)
    _emit_event_async(request, "view_item", item_type="book", item_id=pk)

    try:
        r = http_requests.get(f"{BOOK_SERVICE_URL}/books/{pk}/", timeout=5)
        if r.status_code != 200:
            messages.error(request, "Book not found.")
            return redirect("shop_books")
        book = r.json()
    except Exception:
        messages.error(request, "Book service unavailable.")
        return redirect("shop_books")

    all_reviews = _safe_get(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    book_reviews = [rv for rv in all_reviews if (rv.get("item_type") in (None, "book")) and (rv.get("item_id") == pk or rv.get("book_id") == pk)]

    customers_list = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
    customers_map = {c["id"]: c["name"] for c in customers_list}
    for rv in book_reviews:
        rv["customer_name"] = customers_map.get(rv.get("customer_id"), "Anonymous")

    avg_rating = 0
    if book_reviews:
        avg_rating = round(sum(rv.get("rating", 0) for rv in book_reviews) / len(book_reviews), 1)

    cart_id = None
    if customer:
        cart_id = _get_cart_id(request.session.get("customer_id"))

    if request.method == "POST" and customer:
        action = request.POST.get("action")
        if action == "add_to_cart":
            cid = request.session["customer_id"]
            post_cart_id = request.POST.get("cart_id")
            if not post_cart_id:
                messages.error(request, "Could not find your cart.")
                return redirect("shop_book_detail", pk=pk)
            data = {
                "cart": int(post_cart_id),
                "book_id": pk,
                "quantity": int(request.POST.get("quantity", 1)),
            }
            resp = _safe_post(f"{CART_SERVICE_URL}/cart-items/", data)
            if resp and resp.status_code in (200, 201):
                _emit_event_async(request, "add_to_cart", item_type="book", item_id=pk, metadata={"quantity": data.get("quantity", 1)})
                messages.success(request, f"'{book['title']}' added to your cart!")
            else:
                messages.error(request, "Failed to add item to cart.")
            return redirect("shop_book_detail", pk=pk)

        elif action == "review":
            cid = request.session["customer_id"]
            data = {
                "customer_id": cid,
                "item_type": "book",
                "item_id": pk,
                "book_id": pk,  # backward-compatible
                "rating": int(request.POST.get("rating", 5)),
                "comment": request.POST.get("comment", ""),
            }
            resp = _safe_post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", data)
            if resp and resp.status_code == 201:
                _emit_event_async(request, "review_submit", item_type="book", item_id=pk, metadata={"rating": data.get("rating")})
                messages.success(request, "Review submitted! Thank you.")
            else:
                messages.error(request, "Failed to submit review.")
            return redirect("shop_book_detail", pk=pk)

    catalog_name = ""
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    catalogs_map = {c["id"]: c["name"] for c in catalogs}
    if book.get("catalog_id"):
        catalog_name = catalogs_map.get(book["catalog_id"], "")

    recommendations = []
    if customer:
        cid = request.session["customer_id"]
        recs = _safe_get(f"{RECOMMENDER_SERVICE_URL}/recommendations/{cid}/")
        all_books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
        all_books_map = {b["id"]: b for b in all_books}
        enriched = _enrich_recommendations(recs, all_books_map, catalogs_map)
        # Exclude the current book if it appears as a recommendation.
        recommendations = [r for r in enriched if not (r.get("item_type") == "book" and r.get("item_id") == pk)]

    return render(request, "shop/book_detail.html", {
        "customer": customer,
        "book": book,
        "catalog_name": catalog_name,
        "reviews": book_reviews,
        "avg_rating": avg_rating,
        "cart_id": cart_id,
        "recommendations": recommendations[:4],
    })


# ───────── Browse Clothes ─────────

def shop_clothes(request):
    customer = _get_customer(request)
    _emit_event_async(request, "page_view", metadata={"page": "clothes", "q": request.GET.get("q", ""), "catalog": request.GET.get("catalog", "")})
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    catalogs_map = {c["id"]: c["name"] for c in catalogs}
    products, variants, products_map, variants_map = _load_clothes_data()

    q = request.GET.get("q", "").strip().lower()
    catalog_filter = request.GET.get("catalog", "")
    in_stock = request.GET.get("in_stock", "")
    sort_by = request.GET.get("sort", "")

    # Aggregate per product for listing
    variants_by_product = {}
    for v in variants:
        pid = v.get("product")
        variants_by_product.setdefault(pid, []).append(v)

    items = []
    for p in products:
        pid = p.get("id")
        vs = variants_by_product.get(pid, [])
        if not vs:
            continue
        min_price = min(float(v.get("price", 0)) for v in vs)
        stock_total = sum(int(v.get("stock", 0)) for v in vs)
        item = dict(p)
        item["min_price"] = f"{min_price:.2f}"
        item["stock_total"] = stock_total
        item["catalog_name"] = catalogs_map.get(p.get("catalog_id"), "")
        items.append(item)

    if q:
        items = [p for p in items if q in (p.get("name") or "").lower() or q in (p.get("brand") or "").lower()]

    if catalog_filter:
        try:
            cid = int(catalog_filter)
            items = [p for p in items if p.get("catalog_id") == cid]
        except Exception:
            pass

    if in_stock == "1":
        items = [p for p in items if p.get("stock_total", 0) > 0]

    if sort_by == "price_asc":
        items.sort(key=lambda p: float(p.get("min_price") or 0))
    elif sort_by == "price_desc":
        items.sort(key=lambda p: float(p.get("min_price") or 0), reverse=True)
    elif sort_by == "name":
        items.sort(key=lambda p: (p.get("name") or "").lower())
    elif sort_by == "newest":
        items.sort(key=lambda p: p.get("id", 0), reverse=True)

    return render(request, "shop/clothes.html", {
        "customer": customer,
        "products": items,
        "catalogs": catalogs,
        "catalog_filter": catalog_filter,
        "q": request.GET.get("q", "").strip(),
        "in_stock": in_stock,
        "sort_by": sort_by,
    })


def shop_clothes_detail(request, pk):
    customer = _get_customer(request)
    _emit_event_async(request, "view_item", item_type="clothes_product", item_id=pk)
    try:
        r = http_requests.get(f"{CLOTHES_SERVICE_URL}/products/{pk}/", timeout=5)
        if r.status_code != 200:
            messages.error(request, "Product not found.")
            return redirect("shop_clothes")
        product = r.json()
    except Exception:
        messages.error(request, "Clothes service unavailable.")
        return redirect("shop_clothes")

    variants = _safe_get(f"{CLOTHES_SERVICE_URL}/products/{pk}/variants/")

    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    catalogs_map = {c["id"]: c["name"] for c in catalogs}
    catalog_name = catalogs_map.get(product.get("catalog_id"), "")

    # Reviews are per-variant (item_type=clothes, item_id=variant_id)
    all_reviews = _safe_get(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    variant_ids = {v.get("id") for v in variants}
    reviews = [rv for rv in all_reviews if rv.get("item_type") == "clothes" and rv.get("item_id") in variant_ids]

    customers_list = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
    customers_map = {c["id"]: c["name"] for c in customers_list}
    for rv in reviews:
        rv["customer_name"] = customers_map.get(rv.get("customer_id"), "Anonymous")

    avg_rating = 0
    if reviews:
        avg_rating = round(sum(rv.get("rating", 0) for rv in reviews) / len(reviews), 1)

    cart_id = None
    if customer:
        cart_id = _get_cart_id(request.session.get("customer_id"))

    if request.method == "POST" and customer:
        action = request.POST.get("action")
        if action == "add_to_cart":
            variant_id = request.POST.get("variant_id")
            qty = int(request.POST.get("quantity", 1))
            if not variant_id:
                messages.error(request, "Please select a variant.")
                return redirect("shop_clothes_detail", pk=pk)
            data = {
                "cart": int(request.POST.get("cart_id") or cart_id or 0),
                "item_type": "clothes",
                "item_id": int(variant_id),
                "quantity": qty,
            }
            resp = _safe_post(f"{CART_SERVICE_URL}/cart-items/", data)
            if resp and resp.status_code in (200, 201):
                _emit_event_async(request, "add_to_cart", item_type="clothes_variant", item_id=int(variant_id), metadata={"quantity": qty, "product_id": pk})
                messages.success(request, f"'{product.get('name')}' added to your cart!")
            else:
                messages.error(request, "Failed to add item to cart.")
            return redirect("shop_clothes_detail", pk=pk)

        if action == "review":
            variant_id = request.POST.get("variant_id")
            if not variant_id:
                messages.error(request, "Please select a variant to review.")
                return redirect("shop_clothes_detail", pk=pk)
            data = {
                "customer_id": request.session["customer_id"],
                "item_type": "clothes",
                "item_id": int(variant_id),
                "rating": int(request.POST.get("rating", 5)),
                "comment": request.POST.get("comment", ""),
            }
            resp = _safe_post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", data)
            if resp and resp.status_code == 201:
                _emit_event_async(request, "review_submit", item_type="clothes_variant", item_id=int(variant_id), metadata={"rating": data.get("rating"), "product_id": pk})
                messages.success(request, "Review submitted! Thank you.")
            else:
                messages.error(request, "Failed to submit review.")
            return redirect("shop_clothes_detail", pk=pk)

    # Recommendations (mixed)
    recommendations = []
    if customer:
        cid = request.session["customer_id"]
        recs = _safe_get(f"{RECOMMENDER_SERVICE_URL}/recommendations/{cid}/")
        books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
        books_map = {b["id"]: b for b in books}
        recommendations = _enrich_recommendations(recs, books_map, catalogs_map)[:4]

    return render(request, "shop/clothes_detail.html", {
        "customer": customer,
        "product": product,
        "variants": variants,
        "catalog_name": catalog_name,
        "cart_id": cart_id,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "recommendations": recommendations,
    })


# ───────── Cart ─────────

def shop_cart(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]
    _emit_event_async(request, "page_view", metadata={"page": "cart"})

    if request.method == "POST":
        action = request.POST.get("action")
        item_id = request.POST.get("item_id")

        if action == "update" and item_id:
            new_qty = int(request.POST.get("quantity", 1))
            try:
                r = http_requests.put(
                    f"{CART_SERVICE_URL}/cart-items/{item_id}/",
                    json={"quantity": new_qty}, timeout=5
                )
                if r.status_code == 200:
                    messages.success(request, "Quantity updated.")
                else:
                    messages.error(request, "Failed to update quantity.")
            except Exception:
                messages.error(request, "Cart service unavailable.")
            return redirect("shop_cart")

        elif action == "delete" and item_id:
            try:
                r = http_requests.delete(
                    f"{CART_SERVICE_URL}/cart-items/{item_id}/", timeout=5
                )
                if r.status_code == 204:
                    messages.success(request, "Item removed from cart.")
                else:
                    messages.error(request, "Failed to remove item.")
            except Exception:
                messages.error(request, "Cart service unavailable.")
            return redirect("shop_cart")

    items = []
    cart_id = _get_cart_id(cid)
    error = None
    try:
        r = http_requests.get(f"{CART_SERVICE_URL}/carts/{cid}/", timeout=5)
        if r.status_code == 200:
            items = r.json()
        elif r.status_code == 404:
            error = "Your cart was not found."
    except Exception:
        error = "Cart service unavailable."

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}
    _, _, products_map, variants_map = _load_clothes_data()

    total = 0
    for item in items:
        itype, iid = _get_item_key(item.get("item_type"), item.get("item_id"), item.get("book_id"))
        item["item_type"] = itype
        item["item_id"] = iid
        if itype == "book":
            book = books_map.get(iid)
            item["item_title"] = book["title"] if book else f"Book #{iid}"
            item["item_url"] = f"/books/{iid}/"
            price = float(book["price"]) if book else 0
            stock = book.get("stock", 99) if book else 99
        else:
            variant = variants_map.get(iid)
            product = products_map.get(variant.get("product")) if variant else None
            title = product.get("name") if product else "Clothes"
            desc = " · ".join([x for x in [variant.get("size") if variant else "", variant.get("color") if variant else ""] if x])
            item["item_title"] = f"{title} ({desc})" if desc else title
            item["item_url"] = f"/clothes/{product.get('id')}/" if product else "/clothes/"
            price = float(variant.get("price", 0)) if variant else 0
            stock = int(variant.get("stock", 0)) if variant else 0

        item["unit_price"] = f"{price:.2f}"
        item["stock"] = stock
        subtotal = price * int(item.get("quantity", 0))
        item["subtotal"] = f"{subtotal:.2f}"
        total += subtotal

    return render(request, "shop/cart.html", {
        "customer": customer,
        "items": items,
        "cart_id": cart_id,
        "error": error,
        "total": f"{total:.2f}",
    })


# ───────── Checkout / Place Order ─────────

def shop_checkout(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]
    _emit_event_async(request, "checkout_start")

    if request.method == "POST":
        items_raw = []
        types = request.POST.getlist("item_type")
        ids = request.POST.getlist("item_id")
        quantities = request.POST.getlist("item_quantity")
        prices = request.POST.getlist("item_price")
        for itype, iid, qty, price in zip(types, ids, quantities, prices):
            if itype and iid and qty and price:
                payload = {"item_type": itype, "item_id": int(iid), "quantity": int(qty), "price": price}
                if itype == "book":
                    payload["book_id"] = int(iid)
                items_raw.append(payload)

        data = {
            "customer_id": cid,
            "items": items_raw,
            "payment_method": request.POST.get("payment_method", "credit_card"),
            "shipping_address": request.POST.get("shipping_address", ""),
        }
        r = _safe_post(f"{ORDER_SERVICE_URL}/orders/", data)
        if r and r.status_code == 201:
            _emit_event_async(request, "checkout_complete", metadata={"order_id": r.json().get("id") if hasattr(r, "json") else None})
            messages.success(request, "Order placed successfully! Payment and shipment have been initiated.")
            return redirect("shop_orders")
        else:
            messages.error(request, "Failed to place order. Please try again.")

    items = []
    try:
        r = http_requests.get(f"{CART_SERVICE_URL}/carts/{cid}/", timeout=5)
        if r.status_code == 200:
            items = r.json()
    except Exception:
        pass

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}
    _, _, products_map, variants_map = _load_clothes_data()
    total = 0
    for item in items:
        itype, iid = _get_item_key(item.get("item_type"), item.get("item_id"), item.get("book_id"))
        if itype == "book":
            book = books_map.get(iid)
            title = book["title"] if book else f"Book #{iid}"
            price = float(book["price"]) if book else 0
            url = f"/books/{iid}/"
        else:
            variant = variants_map.get(iid)
            product = products_map.get(variant.get("product")) if variant else None
            title = product.get("name") if product else "Clothes"
            price = float(variant.get("price", 0)) if variant else 0
            url = f"/clothes/{product.get('id')}/" if product else "/clothes/"

        item["item_type"] = itype
        item["item_id"] = iid
        item["item_title"] = title
        item["item_url"] = url
        item["unit_price"] = f"{price:.2f}"
        subtotal = price * int(item.get("quantity", 0))
        item["subtotal"] = f"{subtotal:.2f}"
        total += subtotal

    return render(request, "shop/checkout.html", {
        "customer": customer,
        "items": items,
        "total": f"{total:.2f}",
    })


# ───────── My Orders ─────────

def shop_orders(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]

    if request.method == "POST":
        action = request.POST.get("action")
        order_id = request.POST.get("order_id")

        if action == "change_payment" and order_id:
            payment_id = request.POST.get("payment_id")
            new_method = request.POST.get("payment_method", "").strip()
            if payment_id and new_method:
                r = _safe_put(f"{PAY_SERVICE_URL}/payments/{payment_id}/", {"method": new_method})
                if r and r.status_code == 200:
                    messages.success(request, f"Payment method for Order #{order_id} changed to {new_method}.")
                else:
                    messages.error(request, "Failed to change payment method.")
            else:
                messages.error(request, "Please select a payment method.")

        elif action == "cancel_order" and order_id:
            r = _safe_put(f"{ORDER_SERVICE_URL}/orders/{order_id}/", {"status": "cancelled"})
            if r and r.status_code == 200:
                messages.success(request, f"Order #{order_id} has been cancelled.")
            else:
                messages.error(request, "Failed to cancel order.")

        return redirect("shop_orders")
    _emit_event_async(request, "page_view", metadata={"page": "orders"})

    all_orders = _safe_get(f"{ORDER_SERVICE_URL}/orders/")
    my_orders = [o for o in all_orders if o.get("customer_id") == cid]

    all_payments = _safe_get(f"{PAY_SERVICE_URL}/payments/")
    all_shipments = _safe_get(f"{SHIP_SERVICE_URL}/shipments/")
    payments_map = {p["order_id"]: p for p in all_payments}
    shipments_map = {s["order_id"]: s for s in all_shipments}

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}
    _, _, products_map, variants_map = _load_clothes_data()

    for order in my_orders:
        order["payment"] = payments_map.get(order["id"])
        order["shipment"] = shipments_map.get(order["id"])
        order["can_modify"] = order.get("status") not in ("cancelled", "delivered")
        for item in order.get("items", []):
            itype, iid = _get_item_key(item.get("item_type"), item.get("item_id"), item.get("book_id"))
            if itype == "book":
                book = books_map.get(iid)
                item["item_title"] = book["title"] if book else f"Book #{iid}"
                item["item_url"] = f"/books/{iid}/"
            else:
                variant = variants_map.get(iid)
                product = products_map.get(variant.get("product")) if variant else None
                title = product.get("name") if product else "Clothes"
                desc = " · ".join([x for x in [variant.get("size") if variant else "", variant.get("color") if variant else ""] if x])
                item["item_title"] = f"{title} ({desc})" if desc else title
                item["item_url"] = f"/clothes/{product.get('id')}/" if product else "/clothes/"

    my_orders.sort(key=lambda o: o.get("id", 0), reverse=True)

    payment_methods = [
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("paypal", "PayPal"),
        ("bank_transfer", "Bank Transfer"),
        ("cash_on_delivery", "Cash on Delivery"),
    ]

    return render(request, "shop/orders.html", {
        "customer": customer,
        "orders": my_orders,
        "payment_methods": payment_methods,
    })


# ───────── Reviews ─────────

def shop_reviews(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]

    if request.method == "POST":
        item_type = request.POST.get("item_type") or "book"
        item_id = request.POST.get("item_id")
        if not item_id:
            messages.error(request, "Please select an item to review.")
            return redirect("shop_reviews")
        item_id = int(item_id)
        data = {
            "customer_id": cid,
            "item_type": item_type,
            "item_id": item_id,
            "book_id": item_id if item_type == "book" else None,
            "rating": int(request.POST.get("rating")),
            "comment": request.POST.get("comment", ""),
        }
        r = _safe_post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", data)
        if r and r.status_code == 201:
            _emit_event_async(request, "review_submit", item_type=item_type, item_id=item_id, metadata={"rating": data.get("rating")})
            messages.success(request, "Review submitted! Thank you for your feedback.")
        else:
            messages.error(request, "Failed to submit review.")
        return redirect("shop_reviews")
    _emit_event_async(request, "page_view", metadata={"page": "reviews"})

    all_reviews = _safe_get(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    my_reviews = [rv for rv in all_reviews if rv.get("customer_id") == cid]

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}
    _, _, products_map, variants_map = _load_clothes_data()
    for rv in my_reviews:
        itype, iid = _get_item_key(rv.get("item_type"), rv.get("item_id"), rv.get("book_id"))
        if itype == "book":
            book = books_map.get(iid)
            rv["item_title"] = book["title"] if book else f"Book #{iid}"
            rv["item_url"] = f"/books/{iid}/"
        else:
            variant = variants_map.get(iid)
            product = products_map.get(variant.get("product")) if variant else None
            title = product.get("name") if product else "Clothes"
            desc = " · ".join([x for x in [variant.get("size") if variant else "", variant.get("color") if variant else ""] if x])
            rv["item_title"] = f"{title} ({desc})" if desc else title
            rv["item_url"] = f"/clothes/{product.get('id')}/" if product else "/clothes/"

    return render(request, "shop/reviews.html", {
        "customer": customer,
        "reviews": my_reviews,
        "books": books,
        "clothes_products": list(products_map.values()),
        "clothes_variants": list(variants_map.values()),
    })


# ───────── Account ─────────

def shop_account(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            name = request.POST.get("name", "").strip()
            email = request.POST.get("email", "").strip()
            if not name or not email:
                messages.error(request, "Name and email are required.")
            else:
                data = {"name": name, "email": email}
                r = _safe_put(f"{CUSTOMER_SERVICE_URL}/customers/{cid}/", data)
                if r and r.status_code == 200:
                    request.session["customer_name"] = name
                    messages.success(request, "Profile updated successfully.")
                else:
                    err = "Failed to update profile."
                    try:
                        err = r.json().get("email", [err])[0] if r else err
                    except Exception:
                        pass
                    messages.error(request, err)

        elif action == "change_password":
            current_pw = request.POST.get("current_password", "")
            new_pw = request.POST.get("new_password", "")
            confirm_pw = request.POST.get("confirm_password", "")
            if not current_pw or not new_pw:
                messages.error(request, "All password fields are required.")
            elif new_pw != confirm_pw:
                messages.error(request, "New passwords do not match.")
            elif len(new_pw) < 4:
                messages.error(request, "New password must be at least 4 characters.")
            else:
                verify = _safe_post(
                    f"{CUSTOMER_SERVICE_URL}/customers/login/",
                    {"email": customer["email"], "password": current_pw},
                )
                if verify and verify.status_code == 200:
                    r = _safe_put(f"{CUSTOMER_SERVICE_URL}/customers/{cid}/", {"password": new_pw})
                    if r and r.status_code == 200:
                        messages.success(request, "Password changed successfully.")
                    else:
                        messages.error(request, "Failed to update password.")
                else:
                    messages.error(request, "Current password is incorrect.")

        return redirect("shop_account")

    customer = _get_customer(request)
    return render(request, "shop/account.html", {"customer": customer})


@csrf_exempt
def advisor_chat_proxy(request):
    """
    Proxy endpoint used by the web chat bubble to avoid CORS and
    automatically attach the current session's customer_id when available.
    POST /advisor/chat/  body: {"message": "..."}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        import json

        raw = request.body.decode("utf-8") if request.body else "{}"
        payload_in = json.loads(raw) if raw else {}
    except Exception:
        payload_in = {}

    msg = (payload_in.get("message") or "").strip()
    if not msg:
        return JsonResponse({"error": "message is required"}, status=400)

    customer_id = request.session.get("customer_id")
    payload = {"message": msg, "customer_id": customer_id}

    try:
        r = http_requests.post(f"{ADVISOR_SERVICE_URL}/advisor/chat/", json=payload, timeout=90)
        try:
            out = r.json()
        except Exception:
            out = {"error": "Invalid advisor response"}
        return JsonResponse(out, status=r.status_code)
    except Exception as e:
        return JsonResponse({"error": f"advisor unavailable: {str(e)}"}, status=502)
