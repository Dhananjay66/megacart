from django.shortcuts import render, redirect, get_object_or_404
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
            if 'buy_now_item_id' in request.session:
                cart_items = [get_object_or_404(CartItem, id=request.session['buy_now_item_id'], user=user)]
            else:
                cart_items = CartItem.objects.filter(user=user, order__isnull=True)
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

            # Clear only the relevant cart item(s)
            if 'buy_now_item_id' in request.session:
                CartItem.objects.filter(id=request.session['buy_now_item_id'], user=request.user).delete()
                del request.session['buy_now_item_id']
            else:
                CartItem.objects.filter(user=request.user, order__isnull=True).delete()


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
    payment = Payment.objects.create(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
        delivery_status='Pending',
    )

    order.payment = payment
    order.is_ordered = True
    order.save()

    # Choose cart items based on session
    if 'buy_now_item_id' in request.session:
        cart_items = [get_object_or_404(CartItem, id=request.session['buy_now_item_id'], user=request.user)]
    else:
        cart_items = CartItem.objects.filter(user=request.user, order__isnull=True)

    # Create OrderProduct objects
    for item in cart_items:
        OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=request.user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.price if item.price else item.product.price,
            ordered=True,
        ).variations.set(item.variations.all())

        # Reduce stock
        item.product.stock -= item.quantity
        item.product.save()

    # Delete only the relevant cart items
    if 'buy_now_item_id' in request.session:
        CartItem.objects.filter(id=request.session['buy_now_item_id'], user=request.user).delete()
        del request.session['buy_now_item_id']
    else:
        CartItem.objects.filter(user=request.user, order__isnull=True).delete()

    # Send email
    mail_subject = 'Thank you for your order!'
    message = render_to_string('orders/order_recieved_email.html', {
        'user': request.user,
        'order': order,
    })
    to_email = request.user.email
    EmailMessage(mail_subject, message, to=[to_email]).send()

    return JsonResponse({
        'order_number': order.order_number,
        'transID': payment.payment_id,
    })



def place_order(request, total=0, quantity=0):
    current_user = request.user

    # Check if it's a Buy Now order (single item)
    buy_now_item_id = request.session.get('buy_now_item_id')

    if buy_now_item_id:
        cart_items = [get_object_or_404(CartItem, id=buy_now_item_id, user=current_user)]
        is_buy_now = True
    else:
        cart_items = CartItem.objects.filter(user=current_user, order__isnull=True)
        is_buy_now = False

    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        item_price = cart_item.price if cart_item.price else cart_item.product.price
        total += item_price * cart_item.quantity
        quantity += cart_item.quantity

    tax = round((2 * total) / 100, 2)
    grand_total = round(total + tax, 2)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Save order info
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
            current_date = datetime.date.today().strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # Link order to the cart items (but don’t delete anything here)
            for item in cart_items:
                item.order = data
                item.save()

            context = {
                'order': data,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'is_buy_now': is_buy_now,
                'buy_now_item': cart_items[0] if is_buy_now else None,
            }
            return render(request, 'orders/payments.html', context)

    return redirect('checkout')




def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        payment = Payment.objects.get(payment_id=transID)
        ordered_products = OrderProduct.objects.filter(order=order)

        subtotal = 0
        for item in ordered_products:
            subtotal += item.product_price * item.quantity

        tax = round((2 * subtotal) / 100, 2)
        grand_total = round(subtotal + tax, 2)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
            'tax': tax,
            'grand_total': grand_total,
        }
        return render(request, 'orders/order_complete.html', context)

    except (Order.DoesNotExist, Payment.DoesNotExist):
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
