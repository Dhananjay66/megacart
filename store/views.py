from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery, Variation
from category.models import Category
from carts.models import CartItem
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct

from .forms import ProductForm, VariationForm
from django.contrib.auth.decorators import login_required

from django.forms import inlineformset_factory


def store(request, category_slug=None):
    categories = None
    products = None

    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        paginator = Paginator(products, 3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')
        paginator = Paginator(products, 6)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
    else:
        orderproduct = None

    # Reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    # Product gallery
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)

    # 🔥 Variation price data
    color_variations = Variation.objects.filter(product=single_product, variation_category='color', is_active=True)
    size_variations = Variation.objects.filter(product=single_product, variation_category='size', is_active=True)

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
        'color_variations': color_variations,
        'size_variations': size_variations,
    }
    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated.')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)




# @login_required
@login_required
def add_product(request):
    VariationFormSet = inlineformset_factory(Product, Variation, form=VariationForm, extra=6, can_delete=False)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = VariationFormSet(request.POST)  # ← added this line

        if form.is_valid() and formset.is_valid():
            product = form.save(commit=False)
            product.save()

            formset.instance = product  # link variations to this product
            formset.save()

            return redirect('store')  # or wherever you want to go
    else:
        form = ProductForm()
        formset = VariationFormSet()  # ← added this line

    return render(request, 'store/add_product.html', {
        'form': form,
        'formset': formset,  # ← pass the formset to the template
    })


def check_variation_stock(request):
    product_id = request.GET.get('product_id')
    color = request.GET.get('color')
    size = request.GET.get('size')

    try:
        variations = Variation.objects.filter(product_id=product_id, is_active=True)
        if color:
            variations = variations.filter(variation_category='color', variation_value__iexact=color)
        if size:
            variations = variations.filter(variation_category='size', variation_value__iexact=size)

        if variations.exists():
            return JsonResponse({'available': True})
        else:
            return JsonResponse({'available': False})
    except:
        return JsonResponse({'available': False})


@login_required
def buy_now(request, product_id):
    product = Product.objects.get(id=product_id)
    
    # Get selected variation from POST
    product_variation = []
    if request.method == 'POST':
        for item in request.POST:
            key = item
            value = request.POST[key]
            if key != 'csrfmiddlewaretoken':
                try:
                    variation = product.variation_set.get(variation_category__iexact=key, variation_value__iexact=value)
                    product_variation.append(variation)
                except:
                    pass

    # Delete existing cart items so only selected item goes to checkout
    CartItem.objects.filter(user=request.user).delete()

    # Add only this item to cart
    cart_item = CartItem.objects.create(
        product=product,
        quantity=1,
        user=request.user,
    )
    if len(product_variation) > 0:
        cart_item.variations.add(*product_variation)
    cart_item.save()

    return redirect('checkout')