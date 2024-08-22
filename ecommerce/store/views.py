from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import json
import datetime
from django.views.decorators.csrf import csrf_exempt

from .models import *

from .utils import cookieCart, cartData


def store(request):

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
    else:
        cookieData = cookieCart(request)
        cartItems = cookieData["cartItems"]

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
        cookieData = cookieCart(request)
        cartItems = cookieData["cartItems"]
        order = cookieData["order"]
        items = cookieData["items"]

    context = {"items": items, "order": order, "cartItems": cartItems}
    return render(request, "store/cart.html", context)


def checkout(request):

    data = cartData(request)
    cartItems = data["cartItems"]
    order = data["order"]
    items = data["items"]

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


@csrf_exempt
def processOrder(request):
    try:
        transaction_id = datetime.datetime.now().timestamp()
        data = json.loads(request.body)
        total = float(data["form"]["total"])
        name = data["form"]["name"]
        email = data["form"]["email"]
        items = data.get("items", [])

        if request.user.is_authenticated:
            customer = request.user.customer
            order, created = Order.objects.get_or_create(
                customer=customer, complete=False
            )
        else:
            customer, created = Customer.objects.get_or_create(email=email)
            customer.name = name
            customer.save()
            order = Order.objects.create(customer=customer, complete=False)

        order.transaction_id = transaction_id

        if total == float(order.get_cart_total):
            order.complete = True
        order.save()

        if "shipping" in data:
            ShippingAddress.objects.create(
                customer=customer,
                order=order,
                address=data["shipping"]["address"],
                city=data["shipping"]["city"],
                state=data["shipping"]["state"],
                zipcode=data["shipping"]["zipcode"],
                country=data["shipping"]["country"],
            )

        # Create order items
        for item in items:
            product = Product.objects.get(id=item["product"]["id"])
            OrderItem.objects.create(
                product=product, order=order, quantity=item["quantity"]
            )

        return JsonResponse({"message": "Payment complete!"})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except KeyError as e:
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
