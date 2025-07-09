from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from accounts.models import UserAddress

# Create your views here.
from django.http import HttpResponse

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_variation = []
    variation_price = None
    buy_now = request.POST.get('buy_now') == 'true'

    # Force login if Buy Now
    if buy_now and not request.user.is_authenticated:
        return redirect_to_login(next=request.path)

    if request.method == 'POST':
        for key in request.POST:
            value = request.POST[key]
            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
                if variation.price:
                    variation_price = variation.price
            except:
                pass

    if request.user.is_authenticated:
        current_user = request.user
        cart_items = CartItem.objects.filter(product=product, user=current_user)

        # Check if the exact variation combo exists
        existing_variations = []
        ids = []

        for item in cart_items:
            existing_variations.append(list(item.variations.all()))
            ids.append(item.id)

        if product_variation in existing_variations:
            index = existing_variations.index(product_variation)
            item_id = ids[index]
            cart_item = CartItem.objects.get(id=item_id)
            cart_item.quantity += 1
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(
                product=product,
                user=current_user,
                quantity=1,
                price=variation_price if variation_price else product.price
            )
            if product_variation:
                cart_item.variations.set(product_variation)
            cart_item.save()

        if buy_now:
            request.session['buy_now_item_id'] = cart_item.id
            return redirect('checkout')
        else:
            return redirect('cart')

    else:
        # Guest user
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))

        cart_items = CartItem.objects.filter(product=product, cart=cart)
        existing_variations = []
        ids = []

        for item in cart_items:
            existing_variations.append(list(item.variations.all()))
            ids.append(item.id)

        if product_variation in existing_variations:
            index = existing_variations.index(product_variation)
            item_id = ids[index]
            cart_item = CartItem.objects.get(id=item_id)
            cart_item.quantity += 1
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(
                product=product,
                cart=cart,
                quantity=1,
                price=variation_price if variation_price else product.price
            )
            if product_variation:
                cart_item.variations.set(product_variation)
            cart_item.save()

        return redirect('cart')



def buy_now(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)
    product_variation = []

    if request.method == 'POST':
        for key in request.POST:
            value = request.POST[key]
            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation.id)
            except:
                pass

    # Save to session
    request.session['buy_now'] = {
        'product_id': product.id,
        'variation_ids': product_variation,
        'quantity': 1,
    }

    return redirect('checkout')


def remove_cart(request, product_id, cart_item_id):

    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            if 'buy_now' in request.POST:
                return redirect('checkout')
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')


def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass #just ignore

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax'       : tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)


@login_required(login_url='login')
def checkout(request):
    current_user = request.user
    if not current_user.is_authenticated:
        return redirect('login')

    # Check if it's a Buy Now action
    buy_now_item_id = request.session.get('buy_now_item_id')
    if buy_now_item_id:
        cart_items = [get_object_or_404(CartItem, id=buy_now_item_id, user=current_user)]
    else:
        cart_items = CartItem.objects.filter(user=current_user)


    total = 0
    quantity = 0
    tax = 0
    grand_total = 0
    for cart_item in cart_items:
        item_price = cart_item.price if cart_item.price else cart_item.product.price
        total += item_price * cart_item.quantity
        quantity += cart_item.quantity

    tax = (2 * total) / 100
    grand_total = total + tax
    
    addresses = UserAddress.objects.filter(user=current_user)

    context = {
        'cart_items': cart_items,
        'total': total,
        'quantity': quantity,
        'tax': tax,
        'grand_total': grand_total,
        'addresses': addresses,
    }
    return render(request, 'orders/checkout.html', context)