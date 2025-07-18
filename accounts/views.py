from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm, UserForm, UserProfileForm, UserAddressForm
from .models import Account, UserProfile
from orders.models import Order, OrderProduct
from accounts.models import UserAddress
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse

# Verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

from django.utils.crypto import get_random_string

from django.contrib.auth import login
from django.contrib import messages

from .forms import CompleteProfileForm

from django.core.mail import send_mail
from .models import OTP, Account
from .forms import ContactForm, OTPForm
import random
from django.contrib.auth import login, get_backends
from django.conf import settings
from django.utils import timezone

from carts.models import Cart, CartItem
from carts.views import _cart_id
import requests

from .models import UserAddress
import json


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            username = email.split("@")[0]

            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                role=role,
                username=username,
                password=password
            )
            user.phone_number = phone_number
            user.save()

            # Create profile
            profile = UserProfile(user=user, profile_picture='default/default-user.png')
            profile.save()

            if user.role == 'Customer':
                return redirect('customer_home')
            elif user.role == 'Seller':
                return redirect('add_product')
            elif user.role == 'Admin':
                return redirect('/admin/')


    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

@login_required
def customer_home(request):
    return redirect('login')


def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)

                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))

                    cart_item = CartItem.objects.filter(user=user)
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)

                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save()
            except:
                pass

            auth.login(request, user)
            messages.success(request, 'You are now logged in.')

            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                pass

            # Role-based redirection
            if user.role == 'Admin':
                return redirect('/admin/')  # Admin panel
            elif user.role == 'Seller':
                return redirect('add_product')  # Replace with your actual view name
            elif user.role == 'Customer':
                return redirect('home')  # Replace with your actual view name
            else:
                return redirect('dashboard')  # Fallback

        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required
def seller_dashboard(request):
    return render(request, 'seller/dashboard.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = auth.authenticate(request, email=email, password=password)

        if user is not None:
            auth.login(request, user)

            # Role-based redirection
            if user.role == 'Admin':
                return redirect('/admin/')
            elif user.role == 'Seller':
                return redirect('add_product')
            elif user.role == 'Customer':
                return redirect('home')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')




def send_otp(contact):
    otp = f"{random.randint(100000, 999999)}"
    OTP.objects.create(contact=contact, code=otp)
    send_mail(
        subject='Your OTP Code',
        message=f'Your OTP is: {otp}',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[contact],
    )


def enter_contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.cleaned_data['contact']
            otp_code = f"{random.randint(100000, 999999)}"

            # Save OTP to DB
            OTP.objects.create(contact=contact, code=otp_code)

            # Save email in session for later use
            request.session['contact'] = contact

            # Send email
            send_mail(
                subject='Your OTP Code',
                message=f'Your OTP is: {otp_code}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[contact],
                fail_silently=False,
            )

            return redirect('verify_otp')
    else:
        form = ContactForm()
    return render(request, 'accounts/enter_contact.html', {'form': form})


def verify_otp_view(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            try:
                otp_record = OTP.objects.get(code=entered_otp)
            except OTP.DoesNotExist:
                messages.error(request, 'Invalid OTP.')
                return redirect('verify_otp')

            # Check OTP expiration (5 minutes)
            time_diff = timezone.now() - otp_record.created_at
            if time_diff.total_seconds() > 300:
                messages.error(request, 'OTP has expired.')
                otp_record.delete()
                return redirect('enter_contact')

            contact = otp_record.contact

            # Get or create user
            try:
                user = Account.objects.get(email=contact)
            except Account.DoesNotExist:
                random_password = get_random_string(10)
                user = Account.objects.create_user(
                    email=contact,
                    username=contact.split('@')[0],
                    password=random_password,
                    first_name='',
                    last_name='',
                )

            backend = get_backends()[0].__class__
            user.backend = backend.__module__ + '.' + backend.__name__
            login(request, user)

            messages.success(request, 'Logged in successfully using OTP.')
            otp_record.delete()  # clean up used OTP
            return redirect('dashboard')

    else:
        form = OTPForm()

    return render(request, 'accounts/verify_otp.html', {'form': form})


def login_otp_page(request):
    return render(request, 'accounts/login_otp.html')


@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()

    try:
        userprofile = UserProfile.objects.get(user_id=request.user.id)
    except UserProfile.DoesNotExist:
        userprofile = None

    context = {
        'orders_count': orders_count,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/dashboard.html', context)

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            # Reset password email
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            messages.success(request, 'Password reset email has been sent to your email address.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgotPassword')
    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request, 'This link has been expired!')
        return redirect('login')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password do not match!')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'accounts/my_orders.html', context)


@login_required(login_url='login')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('change_password')
    return render(request, 'accounts/change_password.html')


@login_required(login_url='login')
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)
    subtotal = 0
    for i in order_detail:
        subtotal += i.product_price * i.quantity

    context = {
        'order_detail': order_detail,
        'order': order,
        'subtotal': subtotal,
    }
    return render(request, 'accounts/order_detail.html', context)


def complete_profile(request):
    if request.method == 'POST':
        form = CompleteProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = CompleteProfileForm(instance=request.user)
    return render(request, 'accounts/complete_profile.html', {'form': form})


@login_required
def my_addresses(request):
    addresses = UserAddress.objects.filter(user=request.user)
    return render(request, 'accounts/my_addresses.html', {'addresses': addresses})


@login_required
def add_address(request):
    if request.method == 'POST':
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                # Handle JSON data
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    # Handle form data
                    data = request.POST
                
                # Validate required fields
                required_fields = ['full_name', 'phone', 'address_line_1', 'city', 'state', 'country']
                errors = {}
                
                for field in required_fields:
                    if not data.get(field):
                        errors[field] = [f'{field.replace("_", " ").title()} is required']
                
                # Additional validation
                if data.get('phone') and len(data.get('phone')) != 10:
                    errors['phone'] = ['Please enter a valid 10-digit phone number']
                
                if data.get('postal_code') and len(data.get('postal_code')) != 6:
                    errors['postal_code'] = ['Please enter a valid 6-digit postal code']
                
                if errors:
                    return JsonResponse({
                        'success': False,
                        'errors': errors,
                        'message': 'Please fix the errors below'
                    }, status=400)
                
                # Create address
                address = UserAddress.objects.create(
                    user=request.user,
                    full_name=data.get('full_name'),
                    phone=data.get('phone'),
                    address_line_1=data.get('address_line_1'),
                    address_line_2=data.get('address_line_2', ''),
                    city=data.get('city'),
                    state=data.get('state'),
                    country=data.get('country'),
                    postal_code=data.get('postal_code', ''),
                    is_default=data.get('is_default', False)
                )
                
                # If this is set as default, remove default from other addresses
                if address.is_default:
                    UserAddress.objects.filter(user=request.user).exclude(id=address.id).update(is_default=False)
                
                # If this is the first address, make it default
                if not address.is_default and UserAddress.objects.filter(user=request.user).count() == 1:
                    address.is_default = True
                    address.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Address saved successfully!',
                    'address': {
                        'id': address.id,
                        'full_name': address.full_name,
                        'phone': address.phone,
                        'address_line_1': address.address_line_1,
                        'address_line_2': address.address_line_2,
                        'city': address.city,
                        'state': address.state,
                        'country': address.country,
                        'postal_code': address.postal_code,
                        'is_default': address.is_default
                    }
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data'
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'An error occurred while saving the address'
                }, status=500)
        else:
            # Handle regular form submission
            form = UserAddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                if not UserAddress.objects.filter(user=request.user).exists():
                    address.is_default = True
                address.save()
                messages.success(request, 'Address saved successfully!')
                return redirect('checkout')
            else:
                messages.error(request, 'Please fix the errors below.')
    else:
        form = UserAddressForm()
    
    return render(request, 'accounts/add_address.html', {'form': form})


@login_required
def edit_address(request, id):
    address = get_object_or_404(UserAddress, id=id, user=request.user)
    
    if request.method == 'POST':
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = request.POST
                
                # Validate required fields
                required_fields = ['full_name', 'phone', 'address_line_1', 'city', 'state', 'country']
                errors = {}
                
                for field in required_fields:
                    if not data.get(field):
                        errors[field] = [f'{field.replace("_", " ").title()} is required']
                
                if errors:
                    return JsonResponse({
                        'success': False,
                        'errors': errors,
                        'message': 'Please fix the errors below'
                    }, status=400)
                
                # Update address
                address.full_name = data.get('full_name')
                address.phone = data.get('phone')
                address.address_line_1 = data.get('address_line_1')
                address.address_line_2 = data.get('address_line_2', '')
                address.city = data.get('city')
                address.state = data.get('state')
                address.country = data.get('country')
                address.postal_code = data.get('postal_code', '')
                
                # Handle default status
                if data.get('is_default'):
                    UserAddress.objects.filter(user=request.user).update(is_default=False)
                    address.is_default = True
                
                address.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Address updated successfully!',
                    'redirect_url': '/my-addresses/'  # Change this to your actual URL
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'An error occurred while updating the address'
                }, status=500)
        else:
            # Handle regular form submission
            form = UserAddressForm(request.POST, instance=address)
            if form.is_valid():
                updated = form.save(commit=False)
                if updated.is_default:
                    UserAddress.objects.filter(user=request.user).update(is_default=False)
                updated.save()
                messages.success(request, 'Address updated successfully.')
                return redirect('my_addresses')
            else:
                messages.error(request, 'Please fix the errors below.')
    else:
        form = UserAddressForm(instance=address)
    
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def delete_address(request, id):
    address = get_object_or_404(UserAddress, id=id, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully.')
        return redirect('my_addresses')
    
    return render(request, 'accounts/confirm_delete.html', {'address': address})



@login_required
def set_default_address(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        try:
            # Remove default from all addresses
            UserAddress.objects.filter(user=request.user).update(is_default=False)
            
            # Set new default
            address = UserAddress.objects.get(id=address_id, user=request.user)
            address.is_default = True
            address.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Default address updated successfully!'
            })
        except UserAddress.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Address not found'
            }, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)