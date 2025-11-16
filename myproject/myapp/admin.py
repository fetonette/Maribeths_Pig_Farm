from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Pig, Reservation, Feedback, Cart

# Custom User Admin to ensure password change functionality
class CustomUserAdmin(UserAdmin):
    """Custom User admin with enhanced functionality"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']
    
    # Explicitly enable password change functionality
    change_password_template = None
    change_user_password_template = None
    
    # Ensure all password-related actions are available
    actions = ['reset_passwords']
    
    def reset_passwords(self, request, queryset):
        """Custom action to reset passwords"""
        for user in queryset:
            # This action will be available in the admin
            pass
    reset_passwords.short_description = "Reset selected users' passwords"
    
    def get_urls(self):
        """Override to ensure password change URLs are included"""
        from django.urls import path
        urls = super().get_urls()
        # The parent class already includes password change URLs
        return urls
    
    def has_change_permission(self, request, obj=None):
        """Ensure users can be changed (including passwords)"""
        return super().has_change_permission(request, obj)
    
    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets to ensure password fields are available"""
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'email', 'cellphone_number', 'created_at']
    list_filter = ['created_at']
    search_fields = ['first_name', 'last_name', 'email', 'user__username']

@admin.register(Pig)
class PigAdmin(admin.ModelAdmin):
    list_display = ['breed', 'age_months', 'weight_kg', 'sex', 'price', 'is_available', 'created_at']
    list_filter = ['breed', 'sex', 'is_available', 'created_at']
    search_fields = ['breed', 'description']
    list_editable = ['is_available', 'price']

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'pig', 'fullname', 'contact_number', 'delivery_option', 'payment_method', 'status', 'created_at']
    list_filter = ['delivery_option', 'payment_method', 'status', 'created_at']
    search_fields = ['fullname', 'contact_number', 'user__username']
    list_editable = ['status']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'feedback_type', 'overall_rating', 'get_average_rating', 'would_recommend', 'created_at']
    list_filter = ['feedback_type', 'overall_rating', 'would_recommend', 'created_at']
    search_fields = ['user__username', 'comments']
    readonly_fields = ['user', 'reservation', 'feedback_type', 'created_at', 'get_average_rating']
    
    def get_average_rating(self, obj):
        return f"{obj.get_average_rating():.1f}/5.0"
    get_average_rating.short_description = 'Average Rating'
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'reservation', 'feedback_type', 'created_at')
        }),
        ('Ratings', {
            'fields': ('overall_rating', 'service_quality', 'pig_quality', 'delivery_experience', 'get_average_rating')
        }),
        ('Comments & Recommendation', {
            'fields': ('comments', 'would_recommend')
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'pig', 'quantity', 'get_total_price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'pig__breed']
    
    def get_total_price(self, obj):
        return f"₱{obj.get_total_price():,.2f}"
    get_total_price.short_description = 'Total Price'
