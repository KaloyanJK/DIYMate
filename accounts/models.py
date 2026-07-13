from django.conf import settings
from django.db import models

# Store additional profile information linked to a user account
class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    # Return a readable representation of the user's profile
    def __str__(self):
        return f"Profile for {self.user.username}"

# Store login attempts for security monitoring and auditing
class LoginEvent(models.Model):
    # Define possible login attempt outcomes
    RESULT_SUCCESS = 'success'
    RESULT_FAILED = 'failed'
    RESULT_CHOICES = [
        (RESULT_SUCCESS, 'Success'),
        (RESULT_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='login_events',
        null=True,
        blank=True,
    )
    attempted_identifier = models.CharField(max_length=254, blank=True)
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    # Optional snapshot fields for security/audit context.
    full_name_snapshot = models.CharField(max_length=150, blank=True)
    email_snapshot = models.EmailField(blank=True)
    phone_number_snapshot = models.CharField(max_length=20, blank=True)
    address_snapshot = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Configure default ordering to show latest login events first
    class Meta:
        ordering = ['-created_at']

    # Return a readable representation of a login event
    def __str__(self):
        return f"{self.attempted_identifier or 'unknown'} ({self.result})"


# Store user subscription and payment-related information
class Subscription(models.Model):
    # Define available subscription plans
    PLAN_FREE = 'free'
    PLAN_PREMIUM = 'premium'
    PLAN_CHOICES = [
        (PLAN_FREE, 'Free'),
        (PLAN_PREMIUM, 'Premium'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_FREE)
    is_active = models.BooleanField(default=False)
    ai_usage_count = models.IntegerField(default=0)

    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    renew_date = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Automatically update subscription active status based on selected plan
    def save(self, *args, **kwargs):
        # Keep admin plan changes authoritative: premium means active, free means inactive.
        self.is_active = self.plan == self.PLAN_PREMIUM
        super().save(*args, **kwargs)

    # Return the username associated with the subscription
    def __str__(self):
        return self.user.username