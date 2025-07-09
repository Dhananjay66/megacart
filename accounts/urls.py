from django.urls import path
from . import views
from .views import login_view, complete_profile
from .views import enter_contact_view, verify_otp_view, login_otp_page


urlpatterns = [
    path('register/', views.register, name='register'),

    path('login/', login_view, name='login'),  # Your original login
    
    path('customer/home/', views.customer_home, name='customer_home'),

    path('login_otp/', login_otp_page, name='login_otp'),
    path('otp/', enter_contact_view, name='enter_contact'),  # Enter email
    path('verify/', verify_otp_view, name='verify_otp'),  # OTP entry

    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # path('', views.dashboard, name='dashboard'),

    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('forgotPassword/', views.forgotPassword, name='forgotPassword'),
    path('resetpassword_validate/<uidb64>/<token>/', views.resetpassword_validate, name='resetpassword_validate'),
    path('resetPassword/', views.resetPassword, name='resetPassword'),

    path('my_orders/', views.my_orders, name='my_orders'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),

    path('add_address/', views.add_address, name='add_address'),

    path('set-default-address/', views.set_default_address, name='set_default_address'),
    path('complete-profile/', complete_profile, name='complete_profile'),

]