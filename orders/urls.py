from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),
    path('confirm_payment/', views.confirm_payment, name='confirm_payment'),  # NEW
    path('order_complete/', views.order_complete, name='order_complete'),
    path('invoice/<str:order_number>/<str:payment_id>/', views.download_invoice, name='download_invoice'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
]