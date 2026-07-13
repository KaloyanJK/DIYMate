from django.db import models
from django.conf import settings


# Store DIY project information created by a user
class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.TextField()
    dimensions = models.CharField(max_length=100)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Configure default ordering to display newest projects first
    # Order newest first
    class Meta:
        ordering = ['-created_at']

    # Return the project title as its readable representation
    def __str__(self):
        return self.title