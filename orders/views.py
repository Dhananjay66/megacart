from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from carts.models import CartItem
from accounts.models import UserAddress
import datetime
from .models import Order, Payment, OrderProduct
import json
import os
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib import messages

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
                # Check if OrderProduct already exists to prevent duplicates
                if not OrderProduct.objects.filter(order=order, product=item.product, user=user).exists():
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
            messages.error(request, "Order not found. Please try again.")
            return redirect('checkout')
    
    return redirect('checkout')


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
        # Check if OrderProduct already exists to prevent duplicates
        if not OrderProduct.objects.filter(order=order, product=item.product, user=request.user).exists():
            orderproduct = OrderProduct.objects.create(
                order=order,
                payment=payment,
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.price if item.price else item.product.price,
                ordered=True,
            )
            orderproduct.variations.set(item.variations.all())

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


def place_order(request):
    if request.method == 'POST':
        user = request.user

        # Get cart items
        cart_items = []
        total = 0
        quantity = 0
        tax = 0
        grand_total = 0

        buy_now_item_id = request.session.get('buy_now_item_id')

        if buy_now_item_id:
            cart_item = get_object_or_404(CartItem, id=buy_now_item_id, user=user)
            cart_items = [cart_item]
        else:
            cart_items = CartItem.objects.filter(user=user)

        # Check if cart is empty
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect('store')

        for item in cart_items:
            item_price = item.price if item.price else item.product.price
            total += item_price * item.quantity
            quantity += item.quantity

        tax = (2 * total) / 100
        grand_total = total + tax

        # Check for selected address
        selected_address_id = request.POST.get('address_id')

        if selected_address_id:
            try:
                selected_address = UserAddress.objects.get(id=selected_address_id, user=user)
                address = selected_address
            except UserAddress.DoesNotExist:
                messages.error(request, "Selected address not found.")
                return redirect('checkout')
        else:
            # Get manual form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            full_name = f"{first_name} {last_name}".strip()
            phone = request.POST.get('phone', '').strip()
            address_line_1 = request.POST.get('address_line_1', '').strip()
            address_line_2 = request.POST.get('address_line_2', '').strip()
            city = request.POST.get('city', '').strip()
            state = request.POST.get('state', '').strip()
            country = request.POST.get('country', '').strip()
            
            if not all([full_name, phone, address_line_1, city, state, country]):
                messages.error(request, "Please fill all required address fields or select a saved address.")
                return redirect('checkout')

            # Save this new address
            address = UserAddress.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                country=country,
                postal_code=request.POST.get('postal_code', ''),
            )

        # Create the order
        first_name = address.full_name.split()[0]
        last_name = " ".join(address.full_name.split()[1:]) if len(address.full_name.split()) > 1 else ''
        
        order = Order.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            phone=address.phone,
            email=user.email,
            address_line_1=address.address_line_1,
            address_line_2=address.address_line_2,
            city=address.city,
            state=address.state,
            country=address.country,
            order_total=grand_total,
            tax=tax,
            ip=request.META.get('REMOTE_ADDR'),
        )

        # Generate order number
        current_date = datetime.date.today().strftime("%Y%m%d")
        order_number = current_date + str(order.id)
        order.order_number = order_number
        order.save()  # Don't set is_ordered=True here, it will be set when payment is confirmed
        
        # Create OrderProduct objects (but don't set ordered=True yet)
        for item in cart_items:
            if not OrderProduct.objects.filter(order=order, product=item.product, user=user).exists():
                OrderProduct.objects.create(
                    order=order,
                    user=user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.price if item.price else item.product.price,
                    ordered=False,  # Will be set to True when payment is confirmed
                )
        
        context = {
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total,
            'is_buy_now': bool(buy_now_item_id),
            'buy_now_item': cart_items[0] if buy_now_item_id else None,
        }
        
        return render(request, 'orders/payments.html', context)

    return redirect('checkout')

def edit_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    
    if request.method == 'POST':
        # Update address with form data
        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.address_line_1 = request.POST.get('address_line_1')
        address.address_line_2 = request.POST.get('address_line_2', '')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.country = request.POST.get('country')
        address.postal_code = request.POST.get('postal_code', '')
        
        # Validate required fields
        if not all([address.full_name, address.phone, address.address_line_1, 
                   address.city, address.state, address.country]):
            messages.error(request, "Please fill all required fields.")
            return render(request, 'orders/edit_address.html', {'address': address})
        
        address.save()
        messages.success(request, "Address updated successfully!")
        return redirect('checkout')
    
    return render(request, 'orders/edit_address.html', {'address': address})

def delete_address(request, address_id):
    """View to delete an address"""
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted successfully!")
        return redirect('checkout')
    
    return render(request, 'orders/confirm_delete_address.html', {'address': address})



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
        print("This is order", ordered_products)
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
