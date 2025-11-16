from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="Phone number must be exactly 11 digits starting with 09.")
    cellphone_number = models.CharField(validators=[phone_regex], max_length=11, blank=True)
    address = models.TextField()
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Pig(models.Model):
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    BREED_CHOICES = [
        ('Yorkshire', 'Yorkshire'),
        ('Landrace', 'Landrace'),
        ('Duroc', 'Duroc'),
        ('Hampshire', 'Hampshire'),
        ('Pietrain', 'Pietrain'),
        ('Large White', 'Large White'),
        ('Native', 'Native'),
        ('Crossbreed', 'Crossbreed'),
    ]

    breed = models.CharField(max_length=50, choices=BREED_CHOICES)
    age_months = models.IntegerField(help_text="Age in months")
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, help_text="Weight in kilograms")
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text="Short description of the pig's characteristics")
    picture = models.ImageField(upload_to='pig_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.breed} - {self.get_sex_display()} - {self.get_age_display()}"
    
    def get_age_display(self):
        """Return age in years and months format"""
        if self.age_months >= 12:
            years = self.age_months // 12
            remaining_months = self.age_months % 12
            if remaining_months > 0:
                return f"{years} years {remaining_months} months"
            else:
                return f"{years} years"
        else:
            return f"{self.age_months} months"

class Reservation(models.Model):
    DELIVERY_CHOICES = [
        ('home', 'Delivery'),
        ('pickup', 'Pick up at Farm'),
    ]
    
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('gcash', 'GCash'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Placed Order'),
        ('accepted', 'Placed Order'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pig = models.ForeignKey(Pig, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=17)
    address = models.TextField()
    delivery_option = models.CharField(max_length=10, choices=DELIVERY_CHOICES)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    down_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Required down payment amount")
    proof_of_payment = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    pickup_date = models.DateField(help_text="Date when pig will be picked up or delivered", null=True, blank=True)
    pickup_time = models.TimeField(help_text="Time when pig will be picked up or delivered", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False, help_text="Indicates if the customer has paid for this reservation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reservation by {self.fullname} for {self.pig}"

class PaymentProof(models.Model):
    """Model to store multiple payment proofs for a reservation"""
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='payment_proofs')
    proof_image = models.ImageField(upload_to='payment_proofs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True, help_text="Optional description for this proof")
    
    def __str__(self):
        return f"Payment proof for {self.reservation.fullname} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-uploaded_at']

class DeclineNotification(models.Model):
    """Simple model to store decline notifications for customers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decline_notifications')
    pig_breed = models.CharField(max_length=50)
    pig_price = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Decline notification for {self.user.username} - {self.pig_breed}"
    
    class Meta:
        ordering = ['-created_at']

class Revenue(models.Model):
    """Track completed sales for revenue reporting"""
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    completed_date = models.DateTimeField(auto_now_add=True)
    pig_breed = models.CharField(max_length=50)  # Store for reporting even if pig is deleted
    customer_name = models.CharField(max_length=200)  # Store for reporting
    payment_method = models.CharField(max_length=10)
    
    def __str__(self):
        return f"Revenue: ₱{self.amount} from {self.customer_name} - {self.pig_breed}"
    
    class Meta:
        ordering = ['-completed_date']

class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    FEEDBACK_TYPE_CHOICES = [
        ('reservation', 'Reservation Experience'),
        ('purchase', 'Purchase Experience'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, null=True, blank=True)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    overall_rating = models.IntegerField(choices=RATING_CHOICES)
    service_quality = models.IntegerField(choices=RATING_CHOICES)
    pig_quality = models.IntegerField(choices=RATING_CHOICES)
    delivery_experience = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True, help_text="Additional comments or suggestions")
    would_recommend = models.BooleanField(default=True, help_text="Would you recommend our farm to others?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.user.username} - {self.overall_rating}/5 stars"
    
    def get_average_rating(self):
        """Calculate average rating across all categories"""
        return (self.overall_rating + self.service_quality + self.pig_quality + self.delivery_experience) / 4

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pig = models.ForeignKey(Pig, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'pig')  # Prevent duplicate entries
    
    def __str__(self):
        return f"{self.user.username}'s cart - {self.pig.breed} (Qty: {self.quantity})"
    
    def get_total_price(self):
        return self.pig.price * self.quantity

class Conversation(models.Model):
    """Model for conversation threads between customer and admin"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    subject = models.CharField(max_length=100, default='General Inquiry')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation with {self.user.username}"
    
    def get_latest_message(self):
        return self.messages.first()
    
    def get_unread_count(self):
        return self.messages.filter(is_read=False, sender='customer').count()
    
    def get_unread_admin_replies(self):
        return self.messages.filter(is_read=False, sender='admin').count()

class Message(models.Model):
    """Model for individual messages in conversations"""
    SENDER_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, default='customer')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def get_status(self):
        """Get message status: sent, delivered, or seen"""
        if self.read_at:
            return 'seen'
        elif self.delivered_at:
            return 'delivered'
        else:
            return 'sent'
    
    def __str__(self):
        return f"{self.sender} message in conversation {self.conversation.id}"
