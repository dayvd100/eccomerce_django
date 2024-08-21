from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime

from .models import *


def store(request):

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {"get_cart_total": 0, "get_cart_items": 0}
        cartItems = order["get_cart_items"]

    products = Product.objects.all()
    context = {"products": products, "cartItems": cartItems, "shipping": False}
    return render(request, "store/store.html", context)


def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {"get_orderitem_total": 0, "get_cart_items": 0, "shipping": False}
        cartItems = order["get_cart_items"]

    context = {"items": items, "order": order, "cartItems": cartItems}
    return render(request, "store/cart.html", context)


def checkout(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        items = []
        order = {"get_orderitem_total": 0, "get_cart_items": 0}
        cartItems = order["get_cart_items"]

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "shipping": False,
    }
    return render(request, "store/checkout.html", context)


def updatedItem(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            productId = data.get("productId")
            action = data.get("action")

            if not productId or not action:
                return JsonResponse(
                    {"error": "Missing productId or action"}, status=400
                )

            customer = request.user.customer
            product = Product.objects.get(id=productId)
            order, created = Order.objects.get_or_create(
                customer=customer, complete=False
            )
            orderItem, created = OrderItem.objects.get_or_create(
                order=order, product=product
            )

            if action == "add":
                orderItem.quantity += 1
            elif action == "remove":
                orderItem.quantity -= 1

            if orderItem.quantity <= 0:
                orderItem.delete()
            else:
                orderItem.save()

            return JsonResponse({"message": "Item was updated"})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Product not found"}, status=404)
    return JsonResponse({"error": "Invalid request method"}, status=400)


def processOrder(request):
    try:
        transaction_id = datetime.datetime.now().timestamp()
        data = json.loads(request.body)
        if request.user.is_authenticated:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(
                customer=customer, complete=False
            )
            total = float(data["form"]["total"])
            order.transaction_id = transaction_id

            if total == order.get_cart_total:
                order.complete = True
            order.save()

            if order.shipping:
                ShippingAddress.objects.create(
                    customer=customer,
                    order=order,
                    address=data["shipping"]["address"],
                    city=data["shipping"]["city"],
                    state=data["shipping"]["state"],
                    zipcode=data["shipping"]["zipcode"],
                    country=data["shipping"]["country"],
                )
            return JsonResponse({"message": "Payment complete!"})
        else:
            return JsonResponse({"error": "User is not authenticated"}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except KeyError as e:
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
