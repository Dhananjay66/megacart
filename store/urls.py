from django.urls import path
from . import views

urlpatterns = [
    path('', views.store, name='store'),
    path('add-product/', views.add_product, name='add_product'),
    path('category/<slug:category_slug>/', views.store, name='products_by_category'),
    path('category/<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'),
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),    
    path('check_variation_stock/', views.check_variation_stock, name='check_variation_stock'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
]
