from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
import requests

PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"

class OrderListCreate(APIView):
    def get(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = request.data.get("customer_id")
        items_data = request.data.get("items", [])
        total = sum(float(item.get("price", 0)) * int(item.get("quantity", 0)) for item in items_data)

        order = Order.objects.create(customer_id=customer_id, total_amount=total, status='pending')
        for item in items_data:
            OrderItem.objects.create(
                order=order,
                book_id=item["book_id"],
                quantity=item["quantity"],
                price=item["price"]
            )

        try:
            requests.post(f"{PAY_SERVICE_URL}/payments/", json={
                "order_id": order.id,
                "amount": str(total),
                "method": request.data.get("payment_method", "credit_card"),
            })
        except Exception:
            pass

        try:
            requests.post(f"{SHIP_SERVICE_URL}/shipments/", json={
                "order_id": order.id,
                "address": request.data.get("shipping_address", ""),
            })
        except Exception:
            pass

        order.status = 'confirmed'
        order.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class OrderDetail(APIView):
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        if "status" in request.data:
            order.status = request.data["status"]
            order.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
