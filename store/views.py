from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery, Variation
from category.models import Category
from carts.models import CartItem
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
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
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None

    # Get the reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    # Get the product gallery
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)

    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
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
# def add_product(request):
#     if request.method == 'POST':
#         form = ProductForm(request.POST, request.FILES)
#         if form.is_valid():
#             product = form.save(commit=False)
#             product.save()
#             return redirect('store')  # or a confirmation page
#     else:
#         form = ProductForm()
#     return render(request, 'store/add_product.html', {'form': form})


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

# def add_product(request):
#     ProductFormSet = modelformset_factory(Variation, form=VariationForm, extra=1, can_delete=False)
#     if request.method == 'POST':
#         form = ProductForm(request.POST, request.FILES)
#         formset = ProductFormSet(request.POST)

#         if form.is_valid() and formset.is_valid():
#             product = form.save()
#             for variation_form in formset:
#                 variation = variation_form.save(commit=False)
#                 variation.product = product
#                 variation.save()
#             return redirect('your_success_url')

#     else:
#         form = ProductForm()
#         formset = ProductFormSet(queryset=Variation.objects.none())

#     return render(request, 'add_product.html', {'form': form, 'formset': formset})
