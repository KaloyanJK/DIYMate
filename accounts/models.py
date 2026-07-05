from django.db import models
from django.conf import settings


class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )

    is_active = models.BooleanField(default=False)
    ai_usage_count = models.IntegerField(default=0)

    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    renew_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.username