from django.shortcuts import render, redirect
from django.contrib import messages
import requests as http_requests

BOOK_SERVICE_URL = "http://book-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
STAFF_SERVICE_URL = "http://staff-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
MANAGER_SERVICE_URL = "http://manager-service:8000"


def _safe_get(url):
    try:
        r = http_requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def _safe_post(url, data):
    try:
        r = http_requests.post(url, json=data, timeout=5)
        return r
    except Exception:
        return None


def _safe_put(url, data):
    try:
        r = http_requests.put(url, json=data, timeout=5)
        return r
    except Exception:
        return None


def _safe_delete(url):
    try:
        r = http_requests.delete(url, timeout=5)
        return r
    except Exception:
        return None


def _require_staff(request):
    if not request.session.get("staff_id"):
        messages.warning(request, "Please sign in to access the dashboard.")
        return redirect("dashboard_login")
    return None


# ───────── Dashboard Login / Logout ─────────

def dashboard_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        if email and password:
            r = _safe_post(f"{STAFF_SERVICE_URL}/staffs/login/", {"email": email, "password": password})
            if r and r.status_code == 200:
                staff = r.json()
                request.session["staff_id"] = staff["id"]
                request.session["staff_name"] = staff["name"]
                request.session["staff_position"] = staff.get("position", "")
                messages.success(request, f"Welcome back, {staff['name']}!")
                return redirect("home")
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Please enter both email and password.")
    return render(request, "dashboard_login.html")


def dashboard_logout(request):
    for key in ["staff_id", "staff_name", "staff_position"]:
        request.session.pop(key, None)
    messages.info(request, "You have been signed out of the dashboard.")
    return redirect("dashboard_login")


def home(request):
    redir = _require_staff(request)
    if redir:
        return redir
    return render(request, "home.html")


# ───────── Books ─────────

def book_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            data = {
                "title": request.POST.get("title"),
                "author": request.POST.get("author"),
                "price": request.POST.get("price"),
                "stock": int(request.POST.get("stock", 0)),
            }
            catalog_id = request.POST.get("catalog_id")
            if catalog_id:
                data["catalog_id"] = int(catalog_id)
            r = _safe_post(f"{BOOK_SERVICE_URL}/books/", data)
            if r and r.status_code == 201:
                messages.success(request, f"Book '{data['title']}' added successfully.")
            else:
                messages.error(request, "Failed to add book.")
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {
                "title": request.POST.get("title"),
                "author": request.POST.get("author"),
                "price": request.POST.get("price"),
                "stock": int(request.POST.get("stock", 0)),
            }
            catalog_id = request.POST.get("catalog_id")
            if catalog_id:
                data["catalog_id"] = int(catalog_id)
            r = _safe_put(f"{BOOK_SERVICE_URL}/books/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Book #{pk} updated.")
            else:
                messages.error(request, "Failed to update book.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{BOOK_SERVICE_URL}/books/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Book #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete book.")
        return redirect("book_list")
    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    return render(request, "books.html", {"books": books, "catalogs": catalogs})


# ───────── Customers ─────────

def customer_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "password": request.POST.get("password", "123456"),
            }
            r = _safe_post(f"{CUSTOMER_SERVICE_URL}/customers/", data)
            if r and r.status_code in (200, 201):
                messages.success(request, f"Customer '{data['name']}' registered.")
            else:
                msg = "Failed to register customer."
                try:
                    msg = str(r.json()) if r else msg
                except Exception:
                    pass
                messages.error(request, msg)
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
            }
            r = _safe_put(f"{CUSTOMER_SERVICE_URL}/customers/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Customer #{pk} updated.")
            else:
                messages.error(request, "Failed to update customer.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{CUSTOMER_SERVICE_URL}/customers/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Customer #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete customer.")
        return redirect("customer_list")
    customers = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
    return render(request, "customers.html", {"customers": customers})


# ───────── Cart ─────────

# ───────── Staff ─────────

def staff_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "position": request.POST.get("position"),
                "password": request.POST.get("password", "123456"),
            }
            r = _safe_post(f"{STAFF_SERVICE_URL}/staffs/", data)
            if r and r.status_code == 201:
                messages.success(request, f"Staff '{data['name']}' added.")
            else:
                messages.error(request, "Failed to add staff.")
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "position": request.POST.get("position"),
            }
            r = _safe_put(f"{STAFF_SERVICE_URL}/staffs/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Staff #{pk} updated.")
            else:
                messages.error(request, "Failed to update staff.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{STAFF_SERVICE_URL}/staffs/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Staff #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete staff.")
        return redirect("staff_list")
    staffs = _safe_get(f"{STAFF_SERVICE_URL}/staffs/")
    return render(request, "staffs.html", {"staffs": staffs})


# ───────── Managers ─────────

def manager_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "department": request.POST.get("department"),
            }
            r = _safe_post(f"{MANAGER_SERVICE_URL}/managers/", data)
            if r and r.status_code == 201:
                messages.success(request, f"Manager '{data['name']}' added.")
            else:
                messages.error(request, "Failed to add manager.")
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "department": request.POST.get("department"),
            }
            r = _safe_put(f"{MANAGER_SERVICE_URL}/managers/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Manager #{pk} updated.")
            else:
                messages.error(request, "Failed to update manager.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{MANAGER_SERVICE_URL}/managers/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Manager #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete manager.")
        return redirect("manager_list")
    managers = _safe_get(f"{MANAGER_SERVICE_URL}/managers/")
    return render(request, "managers.html", {"managers": managers})


# ───────── Catalogs ─────────

def catalog_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            data = {
                "name": request.POST.get("name"),
                "description": request.POST.get("description", ""),
            }
            r = _safe_post(f"{CATALOG_SERVICE_URL}/catalogs/", data)
            if r and r.status_code == 201:
                messages.success(request, f"Catalog '{data['name']}' created.")
            else:
                messages.error(request, "Failed to create catalog.")
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {
                "name": request.POST.get("name"),
                "description": request.POST.get("description", ""),
            }
            r = _safe_put(f"{CATALOG_SERVICE_URL}/catalogs/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Catalog #{pk} updated.")
            else:
                messages.error(request, "Failed to update catalog.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{CATALOG_SERVICE_URL}/catalogs/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Catalog #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete catalog.")
        return redirect("catalog_list")
    catalogs = _safe_get(f"{CATALOG_SERVICE_URL}/catalogs/")
    return render(request, "catalogs.html", {"catalogs": catalogs})


# ───────── Orders ─────────

def order_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            items = []
            book_ids = request.POST.getlist("item_book_id")
            quantities = request.POST.getlist("item_quantity")
            prices = request.POST.getlist("item_price")
            for bid, qty, price in zip(book_ids, quantities, prices):
                if bid and qty and price:
                    items.append({"book_id": int(bid), "quantity": int(qty), "price": price})
            data = {
                "customer_id": int(request.POST.get("customer_id")),
                "items": items,
                "payment_method": request.POST.get("payment_method", "credit_card"),
                "shipping_address": request.POST.get("shipping_address", ""),
            }
            r = _safe_post(f"{ORDER_SERVICE_URL}/orders/", data)
            if r and r.status_code == 201:
                messages.success(request, "Order created successfully.")
            else:
                messages.error(request, "Failed to create order.")
        elif action == "edit":
            pk = request.POST.get("pk")
            data = {"status": request.POST.get("status")}
            r = _safe_put(f"{ORDER_SERVICE_URL}/orders/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Order #{pk} updated.")
            else:
                messages.error(request, "Failed to update order.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{ORDER_SERVICE_URL}/orders/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Order #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete order.")
        return redirect("order_list")
    orders = _safe_get(f"{ORDER_SERVICE_URL}/orders/")
    customers = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    return render(request, "orders.html", {"orders": orders, "customers": customers, "books": books})


# ───────── Shipments ─────────

def shipment_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "edit":
            pk = request.POST.get("pk")
            data = {}
            if request.POST.get("status"):
                data["status"] = request.POST.get("status")
            if request.POST.get("tracking_number"):
                data["tracking_number"] = request.POST.get("tracking_number")
            r = _safe_put(f"{SHIP_SERVICE_URL}/shipments/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Shipment #{pk} updated.")
            else:
                messages.error(request, "Failed to update shipment.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{SHIP_SERVICE_URL}/shipments/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Shipment #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete shipment.")
        return redirect("shipment_list")
    shipments = _safe_get(f"{SHIP_SERVICE_URL}/shipments/")
    return render(request, "shipments.html", {"shipments": shipments})


# ───────── Payments ─────────

def payment_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "edit":
            pk = request.POST.get("pk")
            data = {"status": request.POST.get("status")}
            r = _safe_put(f"{PAY_SERVICE_URL}/payments/{pk}/", data)
            if r and r.status_code == 200:
                messages.success(request, f"Payment #{pk} updated.")
            else:
                messages.error(request, "Failed to update payment.")
        elif action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{PAY_SERVICE_URL}/payments/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Payment #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete payment.")
        return redirect("payment_list")
    payments = _safe_get(f"{PAY_SERVICE_URL}/payments/")
    return render(request, "payments.html", {"payments": payments})


# ───────── Reviews ─────────

def review_list(request):
    redir = _require_staff(request)
    if redir:
        return redir
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete":
            pk = request.POST.get("pk")
            r = _safe_delete(f"{COMMENT_RATE_SERVICE_URL}/reviews/{pk}/")
            if r and r.status_code == 204:
                messages.success(request, f"Review #{pk} deleted.")
            else:
                messages.error(request, "Failed to delete review.")
        return redirect("review_list")
    reviews = _safe_get(f"{COMMENT_RATE_SERVICE_URL}/reviews/")
    customers = _safe_get(f"{CUSTOMER_SERVICE_URL}/customers/")
    books = _safe_get(f"{BOOK_SERVICE_URL}/books/")
    customers_map = {c["id"]: c["name"] for c in customers}
    books_map = {b["id"]: b["title"] for b in books}
    for rv in reviews:
        rv["customer_name"] = customers_map.get(rv.get("customer_id"), f"Customer #{rv.get('customer_id')}")
        rv["book_title"] = books_map.get(rv.get("book_id"), f"Book #{rv.get('book_id')}")
    return render(request, "reviews.html", {"reviews": reviews, "customers": customers, "books": books})


