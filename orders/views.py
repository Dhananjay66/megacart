from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from carts.models import CartItem
from .forms import OrderForm
import datetime
from .models import Order, Payment, OrderProduct
import json
import os
from django.conf import settings
from store.models import Product
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from xhtml2pdf import pisa



@csrf_exempt
def confirm_payment(request):
    if request.method == 'POST':
        user = request.user
        order_number = request.POST.get('order_number')
        payment_method = request.POST.get('payment_method')
        amount_paid = request.POST.get('amount_paid')

        try:
            order = Order.objects.get(user=user, is_ordered=False, order_number=order_number)

            payment = Payment.objects.create(
                user=user,
                payment_id=f"PAY-{order_number}",  # Fake ID format
                payment_method=payment_method,
                amount_paid=amount_paid,
                status='Success',
            )

            order.payment = payment
            order.is_ordered = True
            order.save()

            # Move cart items to OrderProduct
            cart_items = CartItem.objects.filter(user=user)
            for item in cart_items:
                orderproduct = OrderProduct.objects.create(
                    order=order,
                    payment=payment,
                    user=user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )
                orderproduct.variations.set(item.variations.all())

                # Reduce stock
                item.product.stock -= item.quantity
                item.product.save()

            # Clear cart
            CartItem.objects.filter(user=user).delete()

            # Send confirmation email
            mail_subject = 'Thank you for your order!'
            message = render_to_string('orders/order_recieved_email.html', {
                'user': user,
                'order': order,
            })
            to_email = user.email
            EmailMessage(mail_subject, message, to=[to_email]).send()

            return redirect(f'/order_complete/?order_number={order.order_number}&payment_id={payment.payment_id}')

        except Order.DoesNotExist:
            return redirect('store')
    return redirect('store')


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    # Store transaction details inside Payment model
    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
        delivery_status='Pending',  # Set initial delivery status
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move cart items to OrderProduct
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order = order
        orderproduct.payment = payment
        orderproduct.user = request.user
        orderproduct.product = item.product
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        orderproduct.variations.set(item.variations.all())
        orderproduct.save()

        # Reduce stock
        product = item.product
        product.stock -= item.quantity
        product.save()

    # Clear the cart
    CartItem.objects.filter(user=request.user).delete()

    # Send order received email
    mail_subject = 'Thank you for your order!'
    message = render_to_string('orders/order_recieved_email.html', {
        'user': request.user,
        'order': order,
    })
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    # Return response
    return JsonResponse({
        'order_number': order.order_number,
        'transID': payment.payment_id,
    })


def place_order(request, total=0, quantity=0,):
    current_user = request.user

    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2 * total)/100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')

def download_invoice(request, order_number, payment_id):
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        payment = Payment.objects.get(payment_id=payment_id)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        for item in ordered_products:
            item.sub_total = item.quantity * item.product_price

        # logo_path = os.path.join(settings.STATIC_ROOT, 'images/logo.png')
        logo_path = os.path.join(settings.BASE_DIR, 'megacart', 'static', 'images', 'logo.png')

        template_path = 'orders/invoice.html'
        context = {
            'order': order,
            'payment': payment,
            'ordered_products': ordered_products,
            'logo_path': logo_path,
        }

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_number}.pdf"'

        template = get_template(template_path)
        html = template.render(context)

        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response

    except (Order.DoesNotExist, Payment.DoesNotExist):
        return redirect('home')
