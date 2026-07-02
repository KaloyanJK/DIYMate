from django.db import models
from django.contrib.auth.models import User

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    ai_usage_count = models.IntegerField(default=0)
    billing_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username