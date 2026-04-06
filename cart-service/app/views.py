from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import requests

BOOK_SERVICE_URL = "http://book-service:8000"
CLOTHES_SERVICE_URL = "http://clothes-service:8000"


def _validate_item(item_type: str, item_id: int) -> bool:
    try:
        if item_type == "book":
            r = requests.get(f"{BOOK_SERVICE_URL}/books/{item_id}/", timeout=5)
            return r.status_code == 200
        if item_type == "clothes":
            r = requests.get(f"{CLOTHES_SERVICE_URL}/variants/{item_id}/", timeout=5)
            return r.status_code == 200
    except Exception:
        return False
    return False


class CartCreate(APIView):
    def post(self, request):
        serializer = CartSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddCartItem(APIView):
    def post(self, request):
        # Backward compatibility: accept book_id OR new fields item_type+item_id.
        item_type = request.data.get("item_type") or ("book" if request.data.get("book_id") is not None else None)
        item_id = request.data.get("item_id") or request.data.get("book_id")
        if item_type is None or item_id is None:
            return Response({"error": "Missing item reference"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item_id = int(item_id)
        except Exception:
            return Response({"error": "Invalid item_id"}, status=status.HTTP_400_BAD_REQUEST)

        if not _validate_item(item_type, item_id):
            return Response({"error": f"{item_type} not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            # Backfill book_id for book items to keep older gateway code working while migrating.
            if obj.item_type == "book" and obj.item_id and obj.book_id is None:
                obj.book_id = obj.item_id
                obj.save(update_fields=["book_id"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetail(APIView):
    def put(self, request, pk):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        quantity = request.data.get("quantity")
        if quantity is not None:
            quantity = int(quantity)
            if quantity < 1:
                return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = quantity
            item.save()
        serializer = CartItemSerializer(item)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartInfo(APIView):
    """Returns the cart object (id + customer_id) for a given customer."""
    def get(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found for this customer"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class ViewCart(APIView):
    def get(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found for this customer"}, status=status.HTTP_404_NOT_FOUND)
        items = CartItem.objects.filter(cart=cart)
        # Backfill generalized fields for legacy rows.
        for it in items:
            if it.item_id is None and it.book_id is not None:
                it.item_type = "book"
                it.item_id = it.book_id
                it.save(update_fields=["item_type", "item_id"])
        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)
