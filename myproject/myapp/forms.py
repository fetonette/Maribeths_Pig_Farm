from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from decimal import Decimal
import re
from .models import Reservation, Pig, Feedback, Message, PaymentProof

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    cellphone_number = forms.CharField(
        max_length=11, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Phone Number',
            'pattern': '[0-9]{11}',
            'maxlength': '11',
            'title': 'Please enter exactly 11 digits'
        })
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'cellphone_number', 'address', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    def clean_cellphone_number(self):
        cellphone_number = self.cleaned_data.get('cellphone_number')
        
        # Remove any non-digit characters
        cleaned_number = re.sub(r'\D', '', cellphone_number)
        
        # Check if exactly 11 digits
        if len(cleaned_number) != 11:
            raise forms.ValidationError('Phone number must be exactly 11 digits.')
        
        # Check if it starts with 09 (Philippine mobile format)
        if not cleaned_number.startswith('09'):
            raise forms.ValidationError('Phone number must start with 09.')
        
        return cleaned_number

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['pig', 'fullname', 'contact_number', 'address', 'delivery_option', 'pickup_date', 'pickup_time', 'payment_method', 'down_payment', 'proof_of_payment']
        widgets = {
            'pig': forms.Select(attrs={'class': 'form-select'}),
            'fullname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact number', 'pattern': '[0-9]{11}', 'maxlength': '11', 'title': 'Please enter exactly 11 digits', 'inputmode': 'numeric', 'oninput': 'this.value = this.value.replace(/[^0-9]/g, "").slice(0, 11)'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter complete address'}),
            'delivery_option': forms.Select(attrs={'class': 'form-select'}),
            'pickup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'down_payment': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter down payment amount', 'min': '0', 'step': '0.01'}),
            'proof_of_payment': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Only show available pigs
        self.fields['pig'].queryset = Pig.objects.filter(is_available=True)
        # Clear default value for down_payment field in new forms
        if not self.instance.pk:  # Only for new instances, not editing existing ones
            self.fields['down_payment'].initial = None
            
        # Auto-populate user profile data for new forms
        if user and not self.instance.pk:
            try:
                # Try to get user profile first
                if hasattr(user, 'userprofile'):
                    profile = user.userprofile
                    self.fields['fullname'].initial = f"{profile.first_name} {profile.last_name}".strip()
                    self.fields['contact_number'].initial = profile.cellphone_number
                    self.fields['address'].initial = profile.address
                else:
                    # Fallback to User model fields if no profile exists
                    full_name = f"{user.first_name} {user.last_name}".strip()
                    if full_name:
                        self.fields['fullname'].initial = full_name
            except Exception:
                # If there's any error, just continue without auto-population
                pass
    
    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number:
            # Remove any non-digit characters
            digits_only = ''.join(filter(str.isdigit, contact_number))
            
            # Check if it's exactly 11 digits
            if len(digits_only) != 11:
                raise forms.ValidationError("Contact number must be exactly 11 digits.")
            
            # Check if it starts with 09 (Philippine mobile number format)
            if not digits_only.startswith('09'):
                raise forms.ValidationError("Contact number must start with 09.")
            
            return digits_only
        return contact_number
        
    def clean(self):
        cleaned_data = super().clean()
        pig = cleaned_data.get('pig')
        down_payment = cleaned_data.get('down_payment')
        
        # Only check pig availability for new reservations, not when editing existing ones
        if pig and not pig.is_available and not self.instance.pk:
            raise forms.ValidationError("This pig is no longer available for reservation.")
        
        # Validate minimum 50% downpayment is provided (including delivery fee)
        if pig and down_payment is not None:
            delivery_option = cleaned_data.get('delivery_option')
            total_price = pig.price
            
            # Add delivery fee if home delivery is selected
            if delivery_option == 'home':
                total_price += Decimal('125')
            
            minimum_payment = total_price * Decimal('0.5')
            if down_payment < minimum_payment:
                delivery_info = " (including ₱125 delivery fee)" if delivery_option == 'home' else ""
                raise forms.ValidationError(
                    f"Minimum 50% down payment required (₱{minimum_payment:.2f}){delivery_info}. "
                    f"You entered ₱{down_payment:.2f}. You can pay any amount equal to or higher than the minimum."
                )
        
        return cleaned_data

class PigForm(forms.ModelForm):
    class Meta:
        model = Pig
        fields = ['breed', 'age_months', 'weight_kg', 'sex', 'price', 'description', 'picture', 'is_available']
        widgets = {
            'breed': forms.Select(attrs={'class': 'form-select'}),
            'age_months': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age in months', 'min': '1'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weight in kg', 'min': '1', 'step': '0.1'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price in PHP', 'min': '0', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Brief description of pig characteristics', 'rows': 3}),
            'picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep current password (for editing)"
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class AdminUserCreateForm(AdminUserForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['overall_rating', 'service_quality', 'pig_quality', 'delivery_experience', 'comments', 'would_recommend']
        widgets = {
            'overall_rating': forms.Select(attrs={'class': 'form-select'}),
            'service_quality': forms.Select(attrs={'class': 'form-select'}),
            'pig_quality': forms.Select(attrs={'class': 'form-select'}),
            'delivery_experience': forms.Select(attrs={'class': 'form-select'}),
            'comments': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Please share your experience and any suggestions for improvement...',
                'rows': 4
            }),
            'would_recommend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'overall_rating': 'Overall Experience',
            'service_quality': 'Service Quality',
            'pig_quality': 'Pig Quality',
            'delivery_experience': 'Delivery/Pickup Experience',
            'comments': 'Additional Comments',
            'would_recommend': 'Would you recommend our farm to others?',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the default value to make checkbox unchecked by default
        if not self.instance.pk:  # Only for new forms, not editing existing feedback
            self.fields['would_recommend'].initial = False

class PurchaseForm(forms.ModelForm):
    """Custom form for immediate purchases - checkout orders are processed immediately with flexible delivery (2-4 days)"""
    payment_method = forms.ChoiceField(
        choices=[('', '---------')] + list(Reservation.PAYMENT_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Payment Method',
        initial=''
    )
    
    class Meta:
        model = Reservation
        fields = ['fullname', 'contact_number', 'address', 'delivery_option', 'pickup_time', 'payment_method', 'proof_of_payment']
        widgets = {
            'fullname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact number', 'pattern': '[0-9]{11}', 'maxlength': '11', 'title': 'Please enter exactly 11 digits', 'inputmode': 'numeric', 'oninput': 'this.value = this.value.replace(/[^0-9]/g, "").slice(0, 11)'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your complete address'}),
            'delivery_option': forms.Select(attrs={'class': 'form-select'}),
            'pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'proof_of_payment': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # pickup_time is required for checkout orders
        
        # Auto-populate user profile data for new forms
        if user and not self.instance.pk:
            try:
                # Try to get user profile first
                if hasattr(user, 'userprofile'):
                    profile = user.userprofile
                    self.fields['fullname'].initial = f"{profile.first_name} {profile.last_name}".strip()
                    self.fields['contact_number'].initial = profile.cellphone_number
                    self.fields['address'].initial = profile.address
                else:
                    # Fallback to User model fields if no profile exists
                    full_name = f"{user.first_name} {user.last_name}".strip()
                    if full_name:
                        self.fields['fullname'].initial = full_name
            except Exception:
                # If there's any error, just continue without auto-population
                pass
    
    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number:
            # Remove any non-digit characters
            digits_only = ''.join(filter(str.isdigit, contact_number))
            
            # Check if it's exactly 11 digits
            if len(digits_only) != 11:
                raise forms.ValidationError("Contact number must be exactly 11 digits.")
            
            # Check if it starts with 09 (Philippine mobile number format)
            if not digits_only.startswith('09'):
                raise forms.ValidationError("Contact number must start with 09.")
            
            return digits_only
        return contact_number
    
    def clean(self):
        cleaned_data = super().clean()
        # No downpayment validation needed for checkout - checkout is for immediate purchase
        return cleaned_data

# MessageForm removed - using direct form handling in views for new conversation system

class PaymentProofForm(forms.ModelForm):
    """Form for adding additional payment proofs"""
    class Meta:
        model = PaymentProof
        fields = ['proof_image', 'description']
        widgets = {
            'proof_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description (e.g., "Down payment", "Final payment")', 'maxlength': 200}),
        }
        labels = {
            'proof_image': 'Upload Additional Proof',
            'description': 'Description (Optional)',
        }
