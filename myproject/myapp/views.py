from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from .models import UserProfile, Pig, Reservation, Feedback, Cart
from .forms import SignUpForm, ReservationForm, PigForm, AdminUserCreateForm, AdminUserForm, FeedbackForm, PurchaseForm

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        # Debug logging
        print(f"Login attempt - Username: {username}, Password length: {len(password) if password else 0}")
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            print(f"Authentication result: {user}")
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    print(f"Login successful for user: {username}")
                    return redirect('home')
                else:
                    messages.error(request, 'Your account has been disabled.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please enter both username and password.')
    
    return render(request, 'registration/login.html')

@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'],
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                UserProfile.objects.create(
                    user=user,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    cellphone_number=form.cleaned_data['cellphone_number'],
                    address=form.cleaned_data['address']
                )
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

# Helper function to check if user is admin
def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
def home_view(request):
    from datetime import date
    from django.db.models import Sum, Count
    from django.db import models
    
    # Basic statistics
    available_pigs = Pig.objects.filter(is_available=True).count()
    total_reservations = Reservation.objects.count()
    
    # Today's statistics
    today = date.today()
    todays_deliveries = Reservation.objects.filter(
        pickup_date=today,
        status__in=['pending', 'confirmed']
    ).values('pig').distinct().count()
    
    # Today's deliveries - orders scheduled for delivery today
    todays_delivery_list = Reservation.objects.filter(
        pickup_date=today,
        status='accepted'  # Only accepted orders scheduled for today
    ).select_related('pig', 'user').order_by('pickup_time')
    
    
    # Today's income (only from completed reservations)
    todays_income = Reservation.objects.filter(
        pickup_date=today,
        status='completed'
    ).aggregate(
        total=Sum('pig__price')
    )['total'] or 0
    
    # Total revenue (all-time from completed reservations)
    total_revenue = Reservation.objects.filter(
        status='completed'
    ).aggregate(
        total=Sum('pig__price')
    )['total'] or 0
    
    # Pending reservations that need admin approval
    pending_reservations = Reservation.objects.filter(
        status='pending'
    ).select_related('pig', 'user').order_by('-created_at')[:5]
    
    # Recent reservations for activity feed (show all recent activity)
    recent_reservations = Reservation.objects.filter(
        status__in=['pending', 'accepted', 'confirmed']
    ).select_related('pig', 'user').order_by('-created_at')[:3]
    
    # Remove recent completed deliveries since we have Today's Deliveries section
    # recent_completed_deliveries = Reservation.objects.filter(
    #     status='completed'
    # ).select_related('pig', 'user').order_by('-updated_at')[:2]
    
    # Low stock notifications (pigs with low availability)
    low_stock_breeds = Pig.objects.filter(is_available=True).values('breed').annotate(
        count=Count('breed')
    ).filter(count__lte=2).order_by('count')[:3]
    
    # Recent pig additions (if you have a created_at field on Pig model)
    try:
        recent_pig_additions = Pig.objects.filter(is_available=True).order_by('-id')[:2]
    except:
        recent_pig_additions = []
    
    context = {
        'available_pigs': available_pigs,
        'total_reservations': total_reservations,
        'todays_deliveries': todays_deliveries,
        'todays_delivery_list': todays_delivery_list,
        'todays_income': todays_income,
        'total_revenue': total_revenue,
        'pending_reservations': pending_reservations,
        'recent_reservations': recent_reservations,
        # 'recent_completed_deliveries': recent_completed_deliveries,
        'low_stock_breeds': low_stock_breeds,
        'recent_pig_additions': recent_pig_additions,
        # Keep legacy variables for backward compatibility
        'total_pigs': available_pigs,
    }
    return render(request, 'myapp/home.html', context)

@login_required
def available_pigs_view(request):
    pigs = Pig.objects.filter(is_available=True)
    
    # Get search parameters
    breed = request.GET.get('breed', '')
    min_weight = request.GET.get('min_weight', '')
    max_weight = request.GET.get('max_weight', '')
    min_age = request.GET.get('min_age', '')
    max_age = request.GET.get('max_age', '')
    age_filter = request.GET.get('age_filter', '')
    
    # Apply age filter (pigs vs piglets)
    if age_filter == 'pigs':
        pigs = pigs.filter(age_months__gte=6)  # 6 months or older = pigs
    elif age_filter == 'piglets':
        pigs = pigs.filter(age_months__lt=6)   # Under 6 months = piglets
    
    # Apply other filters
    if breed:
        pigs = pigs.filter(breed=breed)
    
    if min_weight:
        try:
            pigs = pigs.filter(weight_kg__gte=float(min_weight))
        except ValueError:
            pass
    
    if max_weight:
        try:
            pigs = pigs.filter(weight_kg__lte=float(max_weight))
        except ValueError:
            pass
    
    if min_age:
        try:
            pigs = pigs.filter(age_months__gte=int(min_age))
        except ValueError:
            pass
    
    if max_age:
        try:
            pigs = pigs.filter(age_months__lte=int(max_age))
        except ValueError:
            pass
    
    # Get all available breeds for the dropdown
    available_breeds = Pig.objects.filter(is_available=True).values_list('breed', flat=True).distinct().order_by('breed')
    
    context = {
        'pigs': pigs,
        'available_breeds': available_breeds,
        'search_params': {
            'breed': breed,
            'min_weight': min_weight,
            'max_weight': max_weight,
            'min_age': min_age,
            'max_age': max_age,
            'age_filter': age_filter,
        }
    }
    
    return render(request, 'myapp/available_pigs.html', context)

@login_required
def reservation_view(request, pig_id=None):
    pig = None
    if pig_id:
        pig = get_object_or_404(Pig, id=pig_id, is_available=True)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            if pig:
                reservation.pig = pig
            elif form.cleaned_data.get('pig'):
                reservation.pig = form.cleaned_data['pig']
            reservation.save()
            # Mark pig as unavailable after successful reservation
            if reservation.pig:
                reservation.pig.is_available = False
                reservation.pig.save()
            # Redirect to feedback form for customers only
            if not request.user.is_staff and not request.user.is_superuser:
                # Add success message only for feedback form
                messages.success(request, 'Reservation submitted successfully! Please share your experience.')
                return redirect('feedback_form', reservation_id=reservation.id)
            else:
                messages.success(request, 'Reservation submitted successfully!')
                return redirect('home')
    else:
        form = ReservationForm(user=request.user)
        if pig:
            form.fields['pig'].initial = pig
            form.fields['pig'].widget.attrs['readonly'] = True
    
    return render(request, 'myapp/reservation.html', {'form': form, 'pig': pig})

@login_required
def description_view(request):
    return render(request, 'myapp/description.html')

@login_required
@csrf_exempt
def logout_confirm_view(request):
    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'yes':
            logout(request)
            messages.success(request, 'You have been successfully logged out.')
            return redirect('login')
        elif confirm == 'no':
            return redirect('home')
    return render(request, 'myapp/logout_confirm.html')

# Customer Reservation Management Views
@login_required
def customer_reservation_list(request):
    from datetime import date
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate counts for statistics
    pending_count = reservations.filter(status='pending').count()
    accepted_count = reservations.filter(status='accepted').count()
    
    # Add can_delete flag to each reservation
    today = date.today()
    for reservation in reservations:
        reservation.can_delete = not (reservation.pickup_date and reservation.pickup_date <= today)
    
    context = {
        'reservations': reservations,
        'pending_count': pending_count,
        'accepted_count': accepted_count,
    }
    return render(request, 'myapp/customer_reservation_list.html', context)

@login_required
def customer_reservation_edit(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    if request.method == 'POST':
        form = ReservationForm(request.POST, request.FILES, instance=reservation, user=request.user)
        # For editing, ensure the pig field queryset includes the current pig
        form.fields['pig'].queryset = Pig.objects.filter(id=reservation.pig.id)
        if form.is_valid():
            # Ensure the pig doesn't change during edit
            updated_reservation = form.save(commit=False)
            updated_reservation.pig = reservation.pig  # Keep original pig
            updated_reservation.save()
            messages.success(request, 'Order updated successfully!')
            return redirect('customer_reservation_list')
        else:
            # Debug form errors
            messages.error(request, f'Form validation failed. Please check the fields and try again.')
            for field, errors in form.errors.items():
                messages.error(request, f'{field}: {", ".join(errors)}')
    else:
        form = ReservationForm(instance=reservation, user=request.user)
    return render(request, 'myapp/customer_reservation_form.html', {'form': form, 'title': 'Edit Reservation', 'reservation': reservation})

@login_required
def customer_reservation_delete(request, reservation_id):
    from datetime import date
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Check if reservation can be cancelled
    can_delete = True
    error_message = None
    
    if reservation.status == 'pending':
        # Pending orders can always be cancelled (not yet accepted by admin)
        can_delete = True
    elif reservation.status == 'accepted':
        # Accepted orders can only be cancelled if delivery date hasn't passed
        if reservation.pickup_date and reservation.pickup_date <= date.today():
            can_delete = False
            error_message = "Cannot cancel order. It's already the delivery day or has passed."
    else:
        # Completed orders cannot be cancelled
        can_delete = False
        error_message = "Cannot cancel order. This order has already been completed."
    
    if not can_delete:
        messages.error(request, error_message)
        return redirect('customer_reservation_list')
    
    if request.method == 'POST':
        pig = reservation.pig
        pig.is_available = True
        pig.save()
        reservation.delete()
        messages.success(request, 'Order cancelled successfully!')
        return redirect('customer_reservation_list')
    return render(request, 'myapp/customer_reservation_delete.html', {'reservation': reservation})

@login_required
def purchase_now(request, pig_id):
    pig = get_object_or_404(Pig, id=pig_id, is_available=True)
    from datetime import date
    
    if request.method == 'POST':
        form = PurchaseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.pig = pig
            # Keep the downpayment from the form - don't override it
            reservation.pickup_date = date.today() + timedelta(days=2)  # Auto-set to 2-4 days for purchase delivery
            reservation.save()
            
            pig.is_available = False
            pig.save()
            
            # Don't add success message here as it will persist across redirects
            # Redirect to feedback form for customers only
            if not request.user.is_staff and not request.user.is_superuser:
                # Add success message only for feedback form
                messages.success(request, f'Purchase completed! Pig #{pig.id} is now yours. Please share your experience.')
                return redirect('feedback_form', reservation_id=reservation.id)
            else:
                messages.success(request, f'Purchase completed! Pig #{pig.id} is now yours. Pickup scheduled for tomorrow.')
                return redirect('customer_reservation_list')
        else:
            # Debug form errors
            messages.error(request, f'Form validation failed. Errors: {form.errors}')
    else:
        form = PurchaseForm(initial={'pig': pig}, user=request.user)
        form.fields['pig'].queryset = Pig.objects.filter(id=pig_id)
        form.fields['pig'].widget.attrs['readonly'] = True
    
    return render(request, 'myapp/purchase_now.html', {'form': form, 'pig': pig, 'tomorrow': date.today() + timedelta(days=1)})

# Admin Views
@login_required
@user_passes_test(is_admin)
def admin_pig_add(request):
    if request.method == 'POST':
        form = PigForm(request.POST, request.FILES)
        if form.is_valid():
            pig = form.save(commit=False)
            
            # Custom ID assignment - start from 1 if no pigs exist
            if not Pig.objects.exists():
                # Reset the auto-increment sequence for pig table
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='myapp_pig';")
            
            pig.save()
            messages.success(request, 'Pig added successfully!')
            return redirect('available_pigs')
    else:
        form = PigForm()
    return render(request, 'myapp/admin_pig_form.html', {'form': form, 'title': 'Add New Pig'})

@login_required
@user_passes_test(is_admin)
def admin_pig_edit(request, pig_id):
    pig = get_object_or_404(Pig, id=pig_id)
    if request.method == 'POST':
        form = PigForm(request.POST, request.FILES, instance=pig)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pig updated successfully!')
            return redirect('available_pigs')
    else:
        form = PigForm(instance=pig)
    return render(request, 'myapp/admin_pig_form.html', {'form': form, 'title': 'Edit Pig', 'pig': pig})

@login_required
@user_passes_test(is_admin)
def admin_pig_delete(request, pig_id):
    pig = get_object_or_404(Pig, id=pig_id)
    if request.method == 'POST':
        pig.delete()
        messages.success(request, 'Pig deleted successfully!')
        return redirect('available_pigs')
    return render(request, 'myapp/admin_pig_delete.html', {'pig': pig})

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    # Get search parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset for customers only with accepted reservations count
    from django.db.models import Count, Q
    users = User.objects.filter(is_staff=False, is_superuser=False).annotate(
        accepted_reservations_count=Count('reservation', filter=Q(reservation__status='accepted'))
    )
    
    # Apply search filter
    if search_query:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(userprofile__first_name__icontains=search_query) |
            Q(userprofile__last_name__icontains=search_query)
        ).distinct()
    
    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Order by date joined
    users = users.order_by('-date_joined')
    
    # Calculate statistics (based on all customers, not filtered)
    all_customers = User.objects.filter(is_staff=False, is_superuser=False)
    active_users = all_customers.filter(is_active=True).count()
    admin_count = User.objects.filter(is_staff=True).count()
    customer_count = all_customers.count()
    total_reservations = Reservation.objects.filter(status='accepted').count()
    
    context = {
        'users': users,
        'active_users': active_users,
        'admin_count': admin_count,
        'customer_count': customer_count,
        'total_reservations': total_reservations,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'myapp/admin_user_list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_user_add(request):
    from .forms import AdminUserCreateForm
    
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" has been created successfully!')
            return redirect('admin_user_list')
    else:
        form = AdminUserCreateForm()
    
    return render(request, 'myapp/admin_user_add.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_user_edit(request, user_id):
    from .forms import AdminUserForm
    
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save()
            
            # Also update the UserProfile if it exists
            try:
                profile = user.userprofile
                profile.first_name = user.first_name
                profile.last_name = user.last_name
                profile.email = user.email
                profile.save()
            except UserProfile.DoesNotExist:
                # Create UserProfile if it doesn't exist
                UserProfile.objects.create(
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    cellphone_number='',
                    address=''
                )
            
            messages.success(request, f'User "{user.username}" has been updated successfully!')
            return redirect('admin_user_list')
    else:
        form = AdminUserForm(instance=user_obj)
    
    return render(request, 'myapp/admin_user_edit.html', {'form': form, 'user_obj': user_obj})

@login_required
@user_passes_test(is_admin)
def admin_user_change_password(request, user_id):
    from django.contrib.auth.forms import SetPasswordForm
    
    user_obj = get_object_or_404(User, id=user_id)
    
    # Only allow password changes for regular users (non-staff, non-superuser)
    if user_obj.is_staff or user_obj.is_superuser:
        messages.error(request, 'Cannot change password for admin/staff users!')
        return redirect('admin_user_edit', user_id=user_id)
    
    if request.method == 'POST':
        form = SetPasswordForm(user_obj, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Password for customer "{user.username}" has been changed successfully!')
            return redirect('admin_user_edit', user_id=user_id)
    else:
        form = SetPasswordForm(user_obj)
    
    return render(request, 'myapp/admin_user_change_password.html', {'form': form, 'user_obj': user_obj})

@login_required
@user_passes_test(is_admin)
def admin_user_delete(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    
    # Prevent deletion of superusers
    if user_obj.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts!')
        return redirect('admin_user_list')
    
    if request.method == 'POST':
        # Make associated pigs available again when user is deleted
        for reservation in user_obj.reservation_set.all():
            if reservation.pig:
                reservation.pig.is_available = True
                reservation.pig.save()
        
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f'User "{username}" has been deleted successfully!')
        return redirect('admin_user_list')
    
@login_required
@user_passes_test(is_admin)
def admin_reservation_list(request):
    # Only show accepted reservations in order management
    # Pending reservations are handled through notification system
    # Completed reservations are shown in tracking records
    reservations = Reservation.objects.filter(status='accepted').order_by('-created_at')
    return render(request, 'myapp/admin_reservation_list.html', {'reservations': reservations})

@login_required
@user_passes_test(is_admin)
def admin_reservation_edit(request, reservation_id):
    # ... (rest of the code remains the same)
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'POST':
        # Update reservation fields
        reservation.fullname = request.POST.get('fullname', reservation.fullname)
        reservation.contact_number = request.POST.get('contact_number', reservation.contact_number)
        reservation.address = request.POST.get('address', reservation.address)
        reservation.pickup_date = request.POST.get('pickup_date', reservation.pickup_date)
        reservation.pickup_time = request.POST.get('pickup_time', reservation.pickup_time)
        reservation.payment_method = request.POST.get('payment_method', reservation.payment_method)
        
        try:
            reservation.save()
            messages.success(request, f'Reservation for {reservation.fullname} has been updated successfully!')
            return redirect('admin_reservation_list')
        except Exception as e:
            messages.error(request, f'Error updating reservation: {str(e)}')
    
    return render(request, 'myapp/admin_reservation_edit.html', {'reservation': reservation})

@login_required
@user_passes_test(is_admin)
def admin_reservation_view(request, reservation_id):
    """Read-only view for reservation details"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'myapp/admin_reservation_view.html', {'reservation': reservation})

@login_required
@user_passes_test(is_admin)
def admin_reservation_delete(request, reservation_id):
    from .models import DeclineNotification
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == 'POST':
        # Store reservation details before deletion
        customer_user = reservation.user
        pig_breed = reservation.pig.breed
        pig_price = reservation.pig.price
        
        # Make pig available again
        pig = reservation.pig
        pig.is_available = True
        pig.save()
        
        # Create decline notification for customer
        DeclineNotification.objects.create(
            user=customer_user,
            pig_breed=pig_breed,
            pig_price=pig_price,
            message=f'We\'re sorry, but your order for {pig_breed} pig (₱{pig_price}) has been declined by the admin. You can place a new order if you wish.'
        )
        
        # Delete the reservation
        reservation.delete()
        messages.success(request, f'Order for {reservation.fullname} has been declined. Customer will be notified.')
        return redirect('admin_reservation_list')
    return render(request, 'myapp/admin_reservation_delete.html', {'reservation': reservation})

@login_required
@user_passes_test(is_admin)
def admin_reservation_confirm(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Calculate total price including delivery fee
    total_price = reservation.pig.price
    if reservation.delivery_option == 'home':
        total_price += 125  # Add delivery fee for home delivery
    
    # Check if this is a reservation (requires downpayment) or checkout order (no downpayment required)
    if reservation.down_payment > 0:
        # This is a reservation - validate downpayment
        minimum_payment = total_price * 0.5
        if reservation.down_payment < minimum_payment:
            delivery_info = f" (including ₱125 delivery fee)" if reservation.delivery_option == 'home' else ""
            messages.error(request, f'Cannot accept reservation for {reservation.fullname}: Payment of ₱{reservation.down_payment:,.2f} is insufficient. Minimum 50% down payment required: ₱{minimum_payment:,.2f}{delivery_info}.')
            return redirect('home')
        
        # All validations passed for reservation
        reservation.status = 'accepted'
        reservation.save()
        messages.success(request, f'Reservation for {reservation.fullname} has been accepted! Down payment of ₱{reservation.down_payment:,.2f} confirmed.')
    else:
        # This is a checkout order - no downpayment validation needed
        reservation.status = 'accepted'
        reservation.save()
        messages.success(request, f'Order for {reservation.fullname} has been accepted! Full payment will be collected during delivery/pickup.')
    
    return redirect('home')

@login_required
@user_passes_test(is_admin)
def admin_reservation_complete(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'completed'
    reservation.save()
    messages.success(request, f'Reservation for {reservation.fullname} has been completed! Income recorded: ₱{reservation.pig.price}')
    return redirect('home')

@login_required
@user_passes_test(is_admin)
def admin_reservation_update_status(request, reservation_id):
    """AJAX endpoint to update reservation status"""
    if request.method == 'POST':
        try:
            import json
            from django.http import JsonResponse
            
            reservation = get_object_or_404(Reservation, id=reservation_id)
            data = json.loads(request.body)
            new_status = data.get('status')
            
            # Validate status
            valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            # Update status
            reservation.status = new_status
            reservation.save()
            
            # Create success message
            status_messages = {
                'confirmed': f'Reservation for {reservation.fullname} has been confirmed!',
                'completed': f'Reservation for {reservation.fullname} has been completed!',
                'cancelled': f'Reservation for {reservation.fullname} has been cancelled.',
                'pending': f'Reservation for {reservation.fullname} is now pending.'
            }
            
            messages.success(request, status_messages.get(new_status, 'Status updated successfully!'))
            
            return JsonResponse({
                'success': True, 
                'message': status_messages.get(new_status, 'Status updated successfully!'),
                'new_status': new_status,
                'status_display': reservation.get_status_display()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# User Profile Views
@login_required
def user_profile(request):
    """Display user profile information"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(
            user=request.user,
            first_name=request.user.first_name or '',
            last_name=request.user.last_name or '',
            email=request.user.email or '',
            cellphone_number='',
            address=''
        )
    
    # Get user's reservations
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'profile': profile,
        'reservations': reservations,
        'total_reservations': reservations.count(),
        'pending_reservations': reservations.filter(status='pending').count(),
        'confirmed_reservations': reservations.filter(status='confirmed').count(),
        'completed_reservations': reservations.filter(status='completed').count(),
    }
    
    return render(request, 'myapp/user_profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile information"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            first_name=request.user.first_name or '',
            last_name=request.user.last_name or '',
            email=request.user.email or '',
            cellphone_number='',
            address=''
        )
    
    if request.method == 'POST':
        # Update profile data
        profile.first_name = request.POST.get('first_name', '')
        profile.last_name = request.POST.get('last_name', '')
        profile.email = request.POST.get('email', '')
        profile.cellphone_number = request.POST.get('cellphone_number', '')
        profile.address = request.POST.get('address', '')
        
        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']
        
        # Update User model fields as well
        request.user.first_name = profile.first_name
        request.user.last_name = profile.last_name
        request.user.email = profile.email
        
        try:
            profile.save()
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'myapp/edit_profile.html', {'profile': profile})

@login_required
def change_password(request):
    """Allow customers to change their own password"""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    # Only allow regular users (customers) to change their password
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, 'Password changes are not available for admin users.')
        return redirect('user_profile')
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important! Keep user logged in after password change
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('user_profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'myapp/change_password.html', {'form': form})

@login_required
def feedback_form(request, reservation_id):
    """Display feedback form for customers after reservation/purchase"""
    # Only allow customers (non-staff) to access feedback
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, 'Feedback is only available for customers.')
        return redirect('home')
    
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Check if feedback already exists for this reservation
    existing_feedback = Feedback.objects.filter(user=request.user, reservation=reservation).first()
    if existing_feedback:
        messages.info(request, 'You have already submitted feedback for this reservation.')
        return redirect('customer_reservation_list')
    
    # Determine feedback type based on pickup date
    from datetime import date
    feedback_type = 'purchase' if reservation.pickup_date == reservation.created_at.date() else 'reservation'
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.reservation = reservation
            feedback.feedback_type = feedback_type
            feedback.save()
            
            messages.success(request, 'Thank you for your feedback! Your input helps us improve our service.')
            return redirect('customer_reservation_list')
    else:
        form = FeedbackForm()
    
    context = {
        'form': form,
        'reservation': reservation,
        'feedback_type': feedback_type,
    }
    
    return render(request, 'myapp/feedback_form.html', context)

# Admin Feedback Management Views
@login_required
@user_passes_test(is_admin)
def admin_feedback_list(request):
    """Display all customer feedback for admin review"""
    feedbacks = Feedback.objects.all().order_by('-created_at').select_related('user', 'reservation', 'reservation__pig')
    
    # Calculate statistics
    total_feedbacks = feedbacks.count()
    average_rating = 0
    recommendation_rate = 0
    
    if total_feedbacks > 0:
        total_rating = sum(feedback.get_average_rating() for feedback in feedbacks)
        average_rating = total_rating / total_feedbacks
        recommendations = feedbacks.filter(would_recommend=True).count()
        recommendation_rate = (recommendations / total_feedbacks) * 100
    
    # Filter by rating if requested
    rating_filter = request.GET.get('rating')
    if rating_filter:
        try:
            rating_value = int(rating_filter)
            feedbacks = feedbacks.filter(overall_rating=rating_value)
        except ValueError:
            pass
    
    # Filter by feedback type
    type_filter = request.GET.get('type')
    if type_filter:
        feedbacks = feedbacks.filter(feedback_type=type_filter)
    
    context = {
        'feedbacks': feedbacks,
        'total_feedbacks': total_feedbacks,
        'average_rating': round(average_rating, 1),
        'recommendation_rate': round(recommendation_rate, 1),
        'rating_filter': rating_filter,
        'type_filter': type_filter,
    }
    
    return render(request, 'myapp/admin_feedback_list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_feedback_detail(request, feedback_id):
    """Display detailed view of a specific feedback"""
    feedback = get_object_or_404(Feedback, id=feedback_id)
    
    context = {
        'feedback': feedback,
    }
    
    return render(request, 'myapp/admin_feedback_detail.html', context)

# Cart Views
@login_required
def add_to_cart(request, pig_id):
    """Add a pig to the user's cart"""
    pig = get_object_or_404(Pig, id=pig_id, is_available=True)
    
    # Check if pig is already in cart
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        pig=pig,
        defaults={'quantity': 1}
    )
    
    if not created:
        # If item already exists, show message that it's already in cart
        messages.info(request, f'{pig.breed} is already in your cart!')
    else:
        messages.success(request, f'{pig.breed} added to cart!')
    
    return redirect('available_pigs')

@login_required
def view_cart(request):
    """Display user's cart"""
    # Only show cart items where the pig is still available
    cart_items = Cart.objects.filter(user=request.user, pig__is_available=True).select_related('pig')
    
    # Remove cart items for pigs that are no longer available
    unavailable_items = Cart.objects.filter(user=request.user, pig__is_available=False)
    if unavailable_items.exists():
        unavailable_count = unavailable_items.count()
        unavailable_items.delete()
        messages.info(request, f'{unavailable_count} item(s) removed from cart as they are no longer available.')
    
    # Calculate totals
    total_items = sum(item.quantity for item in cart_items)
    total_price = sum(item.get_total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_items': total_items,
        'total_price': total_price,
    }
    
    return render(request, 'myapp/cart.html', context)

@login_required
def remove_from_cart(request, cart_id):
    """Remove an item from cart"""
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
    pig_name = cart_item.pig.breed
    cart_item.delete()
    messages.success(request, f'{pig_name} removed from cart!')
    return redirect('view_cart')

@login_required
def update_cart_quantity(request, cart_id):
    """Update quantity of cart item"""
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated!')
        else:
            cart_item.delete()
            messages.success(request, f'{cart_item.pig.breed} removed from cart!')
    
    return redirect('view_cart')

@login_required
@csrf_exempt
def checkout_cart(request):
    """Checkout selected items in cart"""
    if request.method == 'POST':
        selected_item_ids = request.POST.getlist('selected_items')
        
        if not selected_item_ids:
            messages.error(request, 'Please select items to checkout!')
            return redirect('view_cart')
        
        # Get selected cart items (only available pigs)
        cart_items = Cart.objects.filter(
            user=request.user, 
            id__in=selected_item_ids,
            pig__is_available=True
        ).select_related('pig')
        
        if not cart_items.exists():
            messages.error(request, 'Selected items not found!')
            return redirect('view_cart')
        
        # If form data is present, process the checkout
        if 'fullname' in request.POST:
            from datetime import date, timedelta
            
            form = PurchaseForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                
                try:
                    with transaction.atomic():
                        # Create reservations for each cart item
                        reservations_created = 0
                        
                        for cart_item in cart_items:
                            # Create reservation with pending status
                            reservation = Reservation.objects.create(
                                user=request.user,
                                pig=cart_item.pig,
                                fullname=form.cleaned_data['fullname'],
                                contact_number=form.cleaned_data['contact_number'],
                                address=form.cleaned_data['address'],
                                delivery_option=form.cleaned_data['delivery_option'],
                                payment_method=form.cleaned_data['payment_method'],
                                down_payment=0,  # Checkout doesn't use downpayment - full payment expected
                                pickup_date=date.today() + timedelta(days=2),  # Checkout orders expected within 2-4 days
                                pickup_time=form.cleaned_data.get('pickup_time'),  # Optional time for checkout orders
                                status='pending'  # Orders start as pending for admin approval
                            )
                            
                            # Handle proof of payment if provided
                            if 'proof_of_payment' in request.FILES:
                                reservation.proof_of_payment = request.FILES['proof_of_payment']
                                reservation.save()
                            
                            reservations_created += 1
                        
                        # Remove selected items from cart after successful checkout
                        cart_items.delete()
                    
                    messages.success(request, f'Checkout successful! {reservations_created} order(s) submitted and waiting for admin approval.')
                    
                    # Redirect to My Orders page to see the pending orders
                    return redirect('customer_reservation_list')
                    
                except Exception as e:
                    messages.error(request, f'Checkout failed: {str(e)}. Please try again.')
                    return redirect('view_cart')
                else:
                    # Form validation failed - show errors
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
                    messages.error(request, 'Please correct the errors below and try again.')
        else:
            # Show checkout form with selected items
            form = PurchaseForm(user=request.user)
            
            # Calculate totals for selected items
            total_items = sum(item.quantity for item in cart_items)
            total_price = sum(item.get_total_price() for item in cart_items)
            # Delivery fee will be calculated dynamically in frontend based on delivery option
            delivery_fee = 125  # Default for display, actual fee determined by delivery option
            final_total = total_price + delivery_fee
            
            context = {
                'form': form,
                'cart_items': cart_items,
                'total_items': total_items,
                'total_price': total_price,
                'delivery_fee': delivery_fee,
                'final_total': final_total,
                'selected_item_ids': selected_item_ids,
            }
            
            return render(request, 'myapp/checkout.html', context)
    
    # If GET request, redirect back to cart
    return redirect('view_cart')

# API endpoint for notification count
@login_required
def admin_status_api(request):
    """API endpoint to check if admin is online"""
    from django.http import JsonResponse
    
    # Simple check - if admin is making this request, they're online
    if request.user.is_superuser or request.user.is_staff:
        return JsonResponse({'is_online': True})
    else:
        return JsonResponse({'is_online': False})

@login_required
@user_passes_test(is_admin)
def user_status_api(request, user_id):
    """API endpoint to check if a specific user is online"""
    from django.http import JsonResponse
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if user has been active in the last 5 minutes
        # You can implement more sophisticated logic here
        # For now, we'll check if they have recent activity
        
        # Simple implementation: check if user has recent messages or login activity
        recent_activity = False
        
        # Check for recent messages (within last 5 minutes)
        from .models import Message
        recent_messages = Message.objects.filter(
            conversation__user=user,
            sender='customer',
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).exists()
        
        if recent_messages:
            recent_activity = True
        
        return JsonResponse({'is_online': recent_activity})
        
    except User.DoesNotExist:
        return JsonResponse({'is_online': False})

# API endpoint for notification count
@login_required
def pending_count_api(request):
    """API endpoint to get pending reservations count for admin notifications"""
    from django.http import JsonResponse
    
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'count': 0})
    
    pending_count = Reservation.objects.filter(status='pending').count()
    return JsonResponse({'count': pending_count})

# API endpoint for pending orders details
@login_required
def decline_notifications_api(request):
    """API endpoint to get decline notifications for customers"""
    from django.http import JsonResponse
    from .models import DeclineNotification
    
    # Get decline notifications for the current user
    notifications = DeclineNotification.objects.filter(user=request.user).order_by('-created_at')
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'pig_breed': notification.pig_breed,
            'pig_price': float(notification.pig_price),
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return JsonResponse({'notifications': notifications_data})

@login_required
def pending_orders_api(request):
    """API endpoint to get pending reservations details for admin notifications"""
    from django.http import JsonResponse
    
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'orders': []})
    
    pending_orders = Reservation.objects.filter(status='pending').select_related('pig', 'user').order_by('-created_at')
    
    orders_data = []
    for order in pending_orders:
        # Calculate total price including delivery fee
        total_price = order.pig.price
        if order.delivery_option == 'home':
            total_price += 125  # Add delivery fee for home delivery
        
        # Calculate required payment based on order type
        if order.down_payment > 0:
            # This is a reservation - 50% minimum downpayment required
            required_payment = total_price * 0.5
        else:
            # This is a checkout order - full payment required during delivery
            required_payment = 0  # No upfront payment required for checkout orders
        
        orders_data.append({
            'id': order.id,
            'fullname': order.fullname,
            'email': order.user.email if order.user and order.user.email else 'Not provided',
            'contact_number': order.contact_number,
            'address': order.address,
            'pig_breed': order.pig.breed,
            'pig_id': order.pig.id,
            'pig_price': int(order.pig.price),
            'down_payment': float(order.down_payment) if order.down_payment else 0,
            'required_payment': float(required_payment),
            'has_proof_of_payment': bool(order.proof_of_payment),
            'delivery_option': order.get_delivery_option_display(),
            'payment_method': order.get_payment_method_display(),
            'pickup_time': order.pickup_time.strftime('%H:%M') if order.pickup_time else 'Not specified',
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({'orders': orders_data})

@login_required
def check_accepted_orders_api(request):
    """API endpoint to check if customer has accepted orders"""
    from django.http import JsonResponse
    
    # Only for customers (non-admin)
    if request.user.is_superuser or request.user.is_staff:
        return JsonResponse({'has_accepted_orders': False, 'count': 0})
    
    # Check for accepted orders that haven't been paid
    accepted_orders = Reservation.objects.filter(
        user=request.user,
        status='accepted',
        is_paid=False
    )
    
    count = accepted_orders.count()
    
    return JsonResponse({
        'has_accepted_orders': count > 0,
        'count': count
    })

@login_required
def get_payment_details_api(request):
    """API endpoint to get payment details for accepted orders"""
    from django.http import JsonResponse
    
    # Only for customers (non-admin)
    if request.user.is_superuser or request.user.is_staff:
        return JsonResponse({'orders': []})
    
    # Get accepted orders that haven't been paid
    accepted_orders = Reservation.objects.filter(
        user=request.user,
        status='accepted',
        is_paid=False
    ).select_related('pig')
    
    orders_data = []
    for order in accepted_orders:
        # Calculate delivery fee based on delivery option
        delivery_fee = 125 if order.delivery_option == 'home' else 0
        total_amount = float(order.pig.price) + delivery_fee
        
        # Calculate remaining balance (total - downpayment)
        downpayment_amount = float(order.down_payment) if order.down_payment else 0
        remaining_balance = total_amount - downpayment_amount
        
        orders_data.append({
            'id': order.id,
            'pig_breed': order.pig.breed,
            'customer_name': order.fullname,
            'pig_price': float(order.pig.price),
            'delivery_fee': delivery_fee,
            'total_amount': total_amount,
            'downpayment_amount': downpayment_amount,
            'remaining_balance': remaining_balance,
            'delivery_option': order.get_delivery_option_display(),
            'payment_method': order.payment_method,
            'payment_method_display': order.get_payment_method_display(),
            'pickup_date': order.pickup_date.strftime('%Y-%m-%d') if order.pickup_date else None,
            'pickup_time': order.pickup_time.strftime('%H:%M') if order.pickup_time else None
        })
    
    return JsonResponse({'orders': orders_data})

@login_required
@csrf_exempt
def upload_payment_proof_api(request, reservation_id):
    """API endpoint to upload multiple proof of payment files for a reservation"""
    from django.http import JsonResponse
    from .models import PaymentProof
    import traceback
    
    if request.method == 'POST':
        try:
            # Verify user owns the reservation
            reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
            
            # Get all uploaded files
            uploaded_files = request.FILES.getlist('proof_of_payment')
            
            if not uploaded_files:
                return JsonResponse({'success': False, 'message': 'No files uploaded. Please select at least one file.'})
            
            # Validate and save each file
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            saved_count = 0
            invalid_files = []
            
            for proof_file in uploaded_files:
                # Validate file type
                file_name = proof_file.name.lower()
                if '.' not in file_name:
                    invalid_files.append(proof_file.name)
                    continue
                    
                file_extension = '.' + file_name.split('.')[-1]
                
                if file_extension not in allowed_extensions:
                    invalid_files.append(proof_file.name)
                    continue
                
                # Create PaymentProof entry
                PaymentProof.objects.create(
                    reservation=reservation,
                    proof_image=proof_file,
                    description=f"Payment proof uploaded on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                )
                saved_count += 1
            
            # Also save to main reservation field if it's empty
            if not reservation.proof_of_payment and uploaded_files:
                reservation.proof_of_payment = uploaded_files[0]
            
            # Mark as paid since customer uploaded proof of payment
            if saved_count > 0:
                reservation.is_paid = True
                reservation.save()
            
            if saved_count > 0:
                message = f'{saved_count} proof(s) of payment uploaded successfully!'
                if invalid_files:
                    message += f' ({len(invalid_files)} file(s) skipped due to invalid format)'
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'files_count': saved_count
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'No valid files uploaded. Only JPG, PNG, or PDF files are allowed.'
                })
            
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error uploading payment proof: {error_trace}")
            return JsonResponse({
                'success': False, 
                'message': f'Error uploading files: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method. Please use POST.'})

@login_required
@user_passes_test(is_admin)
def toggle_payment_status(request, reservation_id):
    """Toggle payment status for a reservation (admin only)"""
    from django.http import JsonResponse
    import json
    
    print(f"toggle_payment_status called with reservation_id: {reservation_id}")
    print(f"Request method: {request.method}")
    print(f"Request body: {request.body}")
    print(f"User: {request.user}")
    print(f"Is admin: {is_admin(request.user)}")
    
    if request.method == 'POST':
        try:
            reservation = get_object_or_404(Reservation, id=reservation_id)
            print(f"Found reservation: {reservation}")
            print(f"Current is_paid status: {reservation.is_paid}")
            
            # Try to get is_paid value from JSON body
            if request.body:
                try:
                    data = json.loads(request.body)
                    print(f"Parsed JSON data: {data}")
                    new_status = data.get('is_paid', not reservation.is_paid)
                    print(f"New status will be: {new_status}")
                    reservation.is_paid = new_status
                    
                    # If marking as paid, complete the order and move to tracking records
                    if new_status:
                        reservation.status = 'completed'
                        print(f"Order marked as completed and will move to tracking records")
                        
                        # Create revenue record if it doesn't exist
                        from .models import Revenue
                        revenue, created = Revenue.objects.get_or_create(
                            reservation=reservation,
                            defaults={
                                'amount': reservation.pig.price,
                                'pig_breed': reservation.pig.breed,
                                'customer_name': reservation.fullname,
                                'payment_method': reservation.payment_method,
                            }
                        )
                        if created:
                            print(f"Created revenue record: {revenue.amount}")
                    else:
                        # If unchecking, revert back to accepted status
                        reservation.status = 'accepted'
                        print(f"Order reverted back to accepted status")
                        
                        # Remove revenue record if it exists
                        from .models import Revenue
                        try:
                            revenue = Revenue.objects.get(reservation=reservation)
                            revenue.delete()
                            print(f"Removed revenue record")
                        except Revenue.DoesNotExist:
                            pass
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    return JsonResponse({'success': False, 'message': f'Invalid JSON data: {str(e)}'})
            else:
                # If no body, just toggle
                print("No request body, toggling status")
                old_paid_status = reservation.is_paid
                reservation.is_paid = not reservation.is_paid
                
                # Apply the same completion logic
                if reservation.is_paid:
                    reservation.status = 'completed'
                    print(f"Order marked as completed and will move to tracking records")
                    
                    # Create revenue record if it doesn't exist
                    from .models import Revenue
                    revenue, created = Revenue.objects.get_or_create(
                        reservation=reservation,
                        defaults={
                            'amount': reservation.pig.price,
                            'pig_breed': reservation.pig.breed,
                            'customer_name': reservation.fullname,
                            'payment_method': reservation.payment_method,
                        }
                    )
                    if created:
                        print(f"Created revenue record: {revenue.amount}")
                else:
                    # If unchecking, revert back to accepted status
                    reservation.status = 'accepted'
                    print(f"Order reverted back to accepted status")
                    
                    # Remove revenue record if it exists
                    from .models import Revenue
                    try:
                        revenue = Revenue.objects.get(reservation=reservation)
                        revenue.delete()
                        print(f"Removed revenue record")
                    except Revenue.DoesNotExist:
                        pass
            
            reservation.save()
            print(f"Saved reservation with is_paid: {reservation.is_paid}")
            
            # Create appropriate success message
            if reservation.is_paid:
                message = f'Order marked as paid and moved to Tracking Records'
            else:
                message = f'Order unmarked and moved back to Order Management'
            
            return JsonResponse({
                'success': True, 
                'is_paid': reservation.is_paid,
                'status': reservation.status,
                'message': message
            })
        except Reservation.DoesNotExist:
            print(f"Reservation {reservation_id} not found")
            return JsonResponse({'success': False, 'message': 'Reservation not found'})
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in toggle_payment_status: {error_trace}")
            return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'})
    
    print(f"Invalid request method: {request.method}")
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def complete_order(request, reservation_id):
    """Complete an order and add to revenue"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # Check if already completed
        if reservation.status == 'completed':
            messages.warning(request, "This order is already completed.")
            return redirect('admin_reservation_list')
        
        # Create revenue record
        from .models import Revenue
        revenue, created = Revenue.objects.get_or_create(
            reservation=reservation,
            defaults={
                'amount': reservation.pig.price,
                'pig_breed': reservation.pig.breed,
                'customer_name': reservation.fullname,
                'payment_method': reservation.payment_method,
            }
        )
        
        # Update reservation status
        reservation.status = 'completed'
        reservation.save()
        
        messages.success(request, f"Order completed! ₱{reservation.pig.price} added to revenue.")
        
    except Exception as e:
        messages.error(request, f"Error completing order: {str(e)}")
    
    return redirect('home')

@login_required
def revenue_dashboard(request):
    """Revenue dashboard for admin"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    from .models import Revenue
    from django.db.models import Sum
    from datetime import datetime, timedelta
    
    # Get revenue statistics
    total_revenue = Revenue.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    # Revenue this month
    current_month = datetime.now().replace(day=1)
    monthly_revenue = Revenue.objects.filter(
        completed_date__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Revenue this week
    week_ago = datetime.now() - timedelta(days=7)
    weekly_revenue = Revenue.objects.filter(
        completed_date__gte=week_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent revenue records
    recent_revenues = Revenue.objects.all()[:10]
    
    context = {
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'weekly_revenue': weekly_revenue,
        'recent_revenues': recent_revenues,
    }
    
    return render(request, 'myapp/revenue_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def tracking_records(request):
    """View for tracking completed orders and sales analytics"""
    from django.db.models import Count, Sum, Q
    from django.db.models.functions import TruncMonth, TruncYear
    from datetime import datetime, timedelta
    import calendar
    
    # Get all completed orders
    completed_orders = Reservation.objects.filter(
        status='completed'
    ).select_related('pig', 'user').order_by('-created_at')
    
    # Monthly sales data for the current year
    current_year = datetime.now().year
    monthly_sales = Reservation.objects.filter(
        status='completed',
        created_at__year=current_year
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('pig__price')
    ).order_by('month')
    
    # Prepare monthly data for chart
    monthly_data = []
    for i in range(1, 13):
        month_name = calendar.month_name[i]
        month_data = next((item for item in monthly_sales if item['month'].month == i), None)
        if month_data:
            monthly_data.append({
                'month': month_name,
                'orders': month_data['total_orders'],
                'revenue': float(month_data['total_revenue'] or 0)
            })
        else:
            monthly_data.append({
                'month': month_name,
                'orders': 0,
                'revenue': 0
            })
    
    # Find peak sales month
    try:
        peak_month = max(monthly_data, key=lambda x: x['orders']) if monthly_data else {'month': 'No Data', 'orders': 0}
    except ValueError:
        peak_month = {'month': 'No Data', 'orders': 0}
    
    # Yearly comparison
    yearly_sales_raw = Reservation.objects.filter(
        status='completed'
    ).annotate(
        year=TruncYear('created_at')
    ).values('year').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('pig__price')
    ).order_by('year')
    
    # Calculate average order value for each year
    yearly_sales = []
    for year_data in yearly_sales_raw:
        avg_order_value = 0
        if year_data['total_orders'] > 0 and year_data['total_revenue']:
            avg_order_value = year_data['total_revenue'] / year_data['total_orders']
        
        yearly_sales.append({
            'year': year_data['year'],
            'total_orders': year_data['total_orders'],
            'total_revenue': year_data['total_revenue'] or 0,
            'avg_order_value': avg_order_value
        })
    
    # Recent 30 days activity
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_orders = completed_orders.filter(created_at__gte=thirty_days_ago)
    
    # Top selling pig breeds
    breed_sales = Reservation.objects.filter(
        status='completed'
    ).values('pig__breed').annotate(
        total_sold=Count('id'),
        total_revenue=Sum('pig__price')
    ).order_by('-total_sold')[:5]
    
    # Summary statistics
    total_completed_orders = completed_orders.count()
    total_revenue = completed_orders.aggregate(
        total=Sum('pig__price')
    )['total'] or 0
    
    import json
    
    # Get all completed logs for comprehensive tracking
    all_completed_logs = Reservation.objects.filter(
        status='completed'
    ).select_related('pig', 'user').order_by('-updated_at')

    context = {
        'completed_orders': completed_orders[:50],  # Show latest 50 orders
        'all_completed_logs': all_completed_logs,  # All completed logs for bottom section
        'monthly_data': monthly_data,
        'monthly_data_json': json.dumps(monthly_data),
        'peak_month': peak_month,
        'yearly_sales': yearly_sales,
        'recent_orders': recent_orders,
        'breed_sales': breed_sales,
        'total_completed_orders': total_completed_orders,
        'total_revenue': total_revenue,
        'current_year': current_year,
    }
    
    return render(request, 'myapp/tracking_records.html', context)

@login_required
def send_message(request):
    """Entry point for customer messaging.

    - For admins: redirect to the admin inbox.
    - For customers: ensure a Conversation exists and open the messenger-style chat
      instead of showing the old contact form page.
    """
    from .models import Conversation, Message

    # If an admin somehow opens this URL, send them to the admin inbox UI
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin_inbox')

    # Determine subject (fallback to General Inquiry). This keeps compatibility
    # if something still posts a subject/message to this view.
    subject = request.POST.get('subject', 'General Inquiry')

    # Get or create a conversation for this user and subject
    conversation, created = Conversation.objects.get_or_create(
        user=request.user,
        subject=subject,
        defaults={'is_active': True}
    )

    # If a message body was submitted (e.g. from the old form), save it once
    message_text = request.POST.get('message')
    if message_text:
        Message.objects.create(
            conversation=conversation,
            sender='customer',
            message=message_text,
            is_read=False
        )
        messages.success(request, 'Your message has been sent successfully!')

    # Always take the customer directly to the messenger-style conversation view
    return redirect('customer_conversation', conversation_id=conversation.id)

@login_required
def my_messages(request):
    """View for customers to see their conversations"""
    from .models import Conversation
    
    user_conversations = Conversation.objects.filter(
        user=request.user, 
        is_active=True
    ).order_by('-updated_at')
    
    return render(request, 'myapp/my_messages.html', {'conversations': user_conversations})

@login_required
def send_reply(request, message_id):
    """View for customers to reply to existing conversations"""
    from .models import Message
    from datetime import datetime
    
    # Get the original message
    original_message = get_object_or_404(Message, id=message_id, user=request.user)
    
    if request.method == 'POST':
        reply_text = request.POST.get('reply_message')
        if reply_text:
            # Create a new message as a reply
            new_message = Message.objects.create(
                user=request.user,
                subject=original_message.subject,
                message=reply_text,
                status='sent'
            )
            messages.success(request, 'Your reply has been sent successfully!')
        else:
            messages.error(request, 'Please enter a message before sending.')
    
    return redirect('my_messages')

@login_required
def delete_conversation(request, message_id):
    """View for customers to delete their conversations"""
    from .models import Message
    
    # Get the message and verify ownership
    message = get_object_or_404(Message, id=message_id, user=request.user)
    
    if request.method == 'POST':
        # Delete all messages with the same subject from the same user
        subject = message.subject
        Message.objects.filter(user=request.user, subject=subject).delete()
        messages.success(request, f'Conversation "{message.get_subject_display()}" has been deleted.')
    
    return redirect('my_messages')

@login_required
@user_passes_test(is_admin)
def admin_inbox(request):
    """Messenger-style inbox view showing all conversations"""
    from .models import Conversation
    from django.db.models import Count, Q
    
    # Get all conversations with latest message and unread count
    conversations = Conversation.objects.filter(is_active=True).select_related('user').annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False, messages__sender='customer'))
    ).order_by('-updated_at')
    
    # Get total unread count
    total_unread = sum(conv.unread_count for conv in conversations)
    
    return render(request, 'myapp/admin_inbox.html', {
        'conversations': conversations,
        'total_unread': total_unread
    })

@login_required
@user_passes_test(is_admin)
def admin_conversation(request, conversation_id):
    """View for admin to see and reply to a specific conversation"""
    from .models import Conversation, Message
    from django.http import JsonResponse
    
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request for sending message
            message_text = request.POST.get('message')
            if message_text:
                # Create new message from admin
                from django.utils import timezone
                new_message = Message.objects.create(
                    conversation=conversation,
                    sender='admin',
                    message=message_text,
                    is_read=True,
                    delivered_at=timezone.now()  # Mark as delivered immediately
                )
                
                # Update conversation timestamp
                conversation.save()  # This will update updated_at

                # Format created_at in local timezone for display
                local_created = timezone.localtime(new_message.created_at)
                
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': new_message.id,
                        'sender': new_message.sender,
                        'message': new_message.message,
                        'created_at': local_created.strftime('%b %d, %Y %I:%M %p')
                    }
                })
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
    
    # Mark all customer messages as read
    from django.utils import timezone
    conversation.messages.filter(sender='customer', is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    # Get all messages in conversation
    messages_list = conversation.messages.all().order_by('created_at')
    
    return render(request, 'myapp/admin_conversation.html', {
        'conversation': conversation,
        'messages': messages_list
    })

@login_required
@user_passes_test(is_admin)
def admin_conversation_delete(request, conversation_id):
    """Delete a conversation and all its messages"""
    from .models import Conversation
    from django.http import JsonResponse
    
    if request.method == 'POST':
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id)
            conversation_user = conversation.user.get_full_name() or conversation.user.username
            
            # Delete the conversation (this will also delete all related messages due to CASCADE)
            conversation.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Conversation with {conversation_user} deleted successfully.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def customer_conversation(request, conversation_id):
    """View for customers to see and reply to their conversation"""
    from .models import Conversation, Message
    from django.http import JsonResponse
    
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request for sending message
            message_text = request.POST.get('message')
            if message_text:
                # Create new message from customer
                from django.utils import timezone
                new_message = Message.objects.create(
                    conversation=conversation,
                    sender='customer',
                    message=message_text,
                    is_read=False,
                    delivered_at=timezone.now()  # Mark as delivered immediately
                )
                
                # Update conversation timestamp
                conversation.save()  # This will update updated_at

                # Format created_at in local timezone for display
                local_created = timezone.localtime(new_message.created_at)
                
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': new_message.id,
                        'sender': new_message.sender,
                        'message': new_message.message,
                        'created_at': local_created.strftime('%b %d, %Y %I:%M %p'),
                        'status': new_message.get_status()
                    }
                })
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
    
    # Mark all admin messages as read
    from django.utils import timezone
    conversation.messages.filter(sender='admin', is_read=False).update(
        is_read=True, 
        read_at=timezone.now()
    )
    
    # Get all messages in conversation
    messages_list = conversation.messages.all().order_by('created_at')
    
    return render(request, 'myapp/customer_conversation.html', {
        'conversation': conversation,
        'messages': messages_list
    })

@login_required
def admin_status_api(request):
    """API endpoint to check if admin is currently active"""
    from django.http import JsonResponse
    from django.contrib.auth.models import User
    from django.utils import timezone
    from datetime import timedelta
    
    # Check if any admin user has been active in the last 5 minutes
    admin_users = User.objects.filter(is_staff=True)
    recent_activity = timezone.now() - timedelta(minutes=5)
    
    # For now, we'll check if any admin has logged in recently
    # In a real app, you'd track actual activity like page views, message sending, etc.
    is_admin_active = admin_users.filter(last_login__gte=recent_activity).exists()
    
    return JsonResponse({'is_online': is_admin_active})

@login_required
@user_passes_test(is_admin)
def admin_create_reservation(request):
    """Admin can create reservations for face-to-face transactions"""
    from django.contrib.auth.models import User
    
    if request.method == 'POST':
        # Get form data
        pig_id = request.POST.get('pig')
        customer_email = request.POST.get('customer_email')
        fullname = request.POST.get('fullname')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        delivery_option = request.POST.get('delivery_option')
        payment_method = request.POST.get('payment_method')
        down_payment = request.POST.get('down_payment', 0)
        pickup_date = request.POST.get('pickup_date')
        pickup_time = request.POST.get('pickup_time')
        status = request.POST.get('status', 'pending')
        
        try:
            # Get or create customer user
            customer_user = None
            if customer_email:
                try:
                    customer_user = User.objects.get(email=customer_email)
                except User.DoesNotExist:
                    # Create new user for the customer
                    username = customer_email.split('@')[0]
                    # Ensure unique username
                    counter = 1
                    original_username = username
                    while User.objects.filter(username=username).exists():
                        username = f"{original_username}{counter}"
                        counter += 1
                    
                    customer_user = User.objects.create_user(
                        username=username,
                        email=customer_email,
                        first_name=fullname.split()[0] if fullname else '',
                        last_name=' '.join(fullname.split()[1:]) if len(fullname.split()) > 1 else ''
                    )
            else:
                # Use admin as user if no customer email provided
                customer_user = request.user
            
            # Get the pig
            pig = get_object_or_404(Pig, id=pig_id, is_available=True)
            
            # Create the reservation
            reservation = Reservation.objects.create(
                user=customer_user,
                pig=pig,
                fullname=fullname,
                contact_number=contact_number,
                address=address,
                delivery_option=delivery_option,
                payment_method=payment_method,
                down_payment=down_payment or 0,
                pickup_date=pickup_date if pickup_date else None,
                pickup_time=pickup_time if pickup_time else None,
                status=status
            )
            
            # Mark pig as unavailable if reservation is accepted or completed
            if status in ['accepted', 'completed']:
                pig.is_available = False
                pig.save()
                
                # Create revenue record if completed
                if status == 'completed':
                    Revenue.objects.create(
                        reservation=reservation,
                        amount=pig.price,
                        pig_breed=pig.breed,
                        customer_name=fullname,
                        payment_method=payment_method
                    )
            
            messages.success(request, f'Reservation created successfully for {fullname}')
            return redirect('admin_reservation_list')
            
        except Exception as e:
            messages.error(request, f'Error creating reservation: {str(e)}')
    
    # Get available pigs for the form
    available_pigs = Pig.objects.filter(is_available=True).order_by('breed', 'age_months')
    
    context = {
        'available_pigs': available_pigs,
        'delivery_choices': Reservation.DELIVERY_CHOICES,
        'payment_choices': Reservation.PAYMENT_CHOICES,
        'status_choices': Reservation.STATUS_CHOICES,
    }
    
    return render(request, 'myapp/admin_create_reservation.html', context)

@login_required
def check_message_status_api(request, conversation_id):
    """API endpoint to check message status updates for a conversation"""
    from .models import Conversation
    from django.http import JsonResponse
    
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        
        # Get all customer messages in this conversation
        customer_messages = conversation.messages.filter(sender='customer').values(
            'id', 'is_read', 'read_at', 'delivered_at'
        )
        
        # Format message statuses
        message_statuses = {}
        for msg in customer_messages:
            if msg['read_at']:
                status = 'seen'
            elif msg['delivered_at']:
                status = 'delivered'
            else:
                status = 'sent'
            message_statuses[msg['id']] = status
        
        return JsonResponse({
            'success': True,
            'message_statuses': message_statuses
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
