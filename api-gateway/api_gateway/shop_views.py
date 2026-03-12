from django.shortcuts import render, redirect
from django.contrib import messages
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


# ───────── Home ─────────

def shop_home(request):
    customer = _get_customer(request)
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
        for rec in recommendations:
            book = books_map.get(rec.get("book_id"))
            if book:
                rec["book_title"] = book["title"]
                rec["book_author"] = book["author"]
                rec["book_price"] = book["price"]
                rec["book_stock"] = book.get("stock", 0)
                rec["catalog_name"] = catalogs_map.get(book.get("catalog_id"), "")
        recommendations.sort(key=lambda r: r.get("score", 0), reverse=True)

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
                messages.success(request, f"Welcome back, {customer['name']}!")
                return redirect("shop_home")
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please enter both email and password.")
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
                messages.success(request, f"Welcome, {name}! Your account and cart have been created.")
                return redirect("shop_home")
            else:
                messages.error(request, "Registration failed. Email may already be in use.")
    return render(request, "shop/login.html", {"customer": None, "show_register": True})


def shop_logout(request):
    request.session.flush()
    messages.info(request, "You have been signed out.")
    return redirect("shop_home")


# ───────── Browse Books ─────────

def shop_books(request):
    customer = _get_customer(request)
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
    book_reviews = [rv for rv in all_reviews if rv.get("book_id") == pk]

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
                messages.success(request, f"'{book['title']}' added to your cart!")
            else:
                messages.error(request, "Failed to add item to cart.")
            return redirect("shop_book_detail", pk=pk)

        elif action == "review":
            cid = request.session["customer_id"]
            data = {
                "customer_id": cid,
                "book_id": pk,
                "rating": int(request.POST.get("rating", 5)),
                "comment": request.POST.get("comment", ""),
            }
            resp = _safe_post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", data)
            if resp and resp.status_code == 201:
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
        for rec in recs:
            if rec.get("book_id") == pk:
                continue
            rb = all_books_map.get(rec.get("book_id"))
            if rb:
                rec["book_title"] = rb["title"]
                rec["book_author"] = rb["author"]
                rec["book_price"] = rb["price"]
                rec["book_stock"] = rb.get("stock", 0)
                rec["catalog_name"] = catalogs_map.get(rb.get("catalog_id"), "")
                recommendations.append(rec)
        recommendations.sort(key=lambda r: r.get("score", 0), reverse=True)

    return render(request, "shop/book_detail.html", {
        "customer": customer,
        "book": book,
        "catalog_name": catalog_name,
        "reviews": book_reviews,
        "avg_rating": avg_rating,
        "cart_id": cart_id,
        "recommendations": recommendations[:4],
    })


# ───────── Cart ─────────

def shop_cart(request):
    redir = _require_login(request)
    if redir:
        return redir
    customer = _get_customer(request)
    cid = request.session["customer_id"]

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

    total = 0
    for item in items:
        book = books_map.get(item["book_id"])
        if book:
            item["book_title"] = book["title"]
            item["book_price"] = book["price"]
            item["book_stock"] = book.get("stock", 99)
            try:
                subtotal = float(book["price"]) * item["quantity"]
            except (ValueError, TypeError):
                subtotal = 0
            item["subtotal"] = f"{subtotal:.2f}"
            total += subtotal
        else:
            item["book_title"] = f"Book #{item['book_id']}"
            item["book_price"] = "N/A"
            item["book_stock"] = 99
            item["subtotal"] = "N/A"

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

    if request.method == "POST":
        items_raw = []
        book_ids = request.POST.getlist("item_book_id")
        quantities = request.POST.getlist("item_quantity")
        prices = request.POST.getlist("item_price")
        for bid, qty, price in zip(book_ids, quantities, prices):
            if bid and qty and price:
                items_raw.append({"book_id": int(bid), "quantity": int(qty), "price": price})

        data = {
            "customer_id": cid,
            "items": items_raw,
            "payment_method": request.POST.get("payment_method", "credit_card"),
            "shipping_address": request.POST.get("shipping_address", ""),
        }
        r = _safe_post(f"{ORDER_SERVICE_URL}/orders/", data)
        if r and r.status_code == 201:
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
    total = 0
    for item in items:
        book = books_map.get(item["book_id"])
        if book:
            item["book_title"] = book["title"]
            item["book_price"] = book["price"]
            try:
                subtotal = float(book["price"]) * item["quantity"]
            except (ValueError, TypeError):
                subtotal = 0
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

    all_orders = _safe_get(f"{ORDER_SERVICE_URL}/orders/")
    my_orders = [o for o in all_orders if o.get("customer_id") == cid]

    all_payments = _safe_get(f"{PAY_SERVICE_URL}/payments/")
    all_shipments = _safe_get(f"{SHIP_SERVICE_URL}/shipments/")
    payments_map = {p["order_id"]: p for p in all_payments}
    shipments_map = {s["order_id"]: s for s in all_shipments}

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}

    for order in my_orders:
        order["payment"] = payments_map.get(order["id"])
        order["shipment"] = shipments_map.get(order["id"])
        order["can_modify"] = order.get("status") not in ("cancelled", "delivered")
        for item in order.get("items", []):
            book = books_map.get(item.get("book_id"))
            item["book_title"] = book["title"] if book else "Book"

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
        data = {
            "customer_id": cid,
            "book_id": int(request.POST.get("book_id")),
            "rating": int(request.POST.get("rating")),
            "comment": request.POST.get("comment", ""),
        }
        r = _safe_post(f"{COMMENT_RATE_SERVICE_URL}/reviews/", data)
        if r and r.status_code == 201:
            messages.success(request, "Review submitted! Thank you for your feedback.")
        else:
            messages.error(request, "Failed to submit review.")
        return redirect("shop_reviews")

    all_reviews = _safe_get(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    my_reviews = [rv for rv in all_reviews if rv.get("customer_id") == cid]

    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    books_map = {b["id"]: b for b in books}
    for rv in my_reviews:
        book = books_map.get(rv["book_id"])
        rv["book_title"] = book["title"] if book else f"Book #{rv['book_id']}"

    return render(request, "shop/reviews.html", {
        "customer": customer,
        "reviews": my_reviews,
        "books": books,
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
