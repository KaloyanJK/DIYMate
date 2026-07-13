from django import forms
from accounts.services import get_or_create_subscription

from .models import Project


# Create a form for creating and editing DIY projects
class ProjectForm(forms.ModelForm):
    # Initialize the project form and restrict fields based on user subscription
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user is None:
            return

        subscription = get_or_create_subscription(user)
        if subscription.plan != subscription.PLAN_PREMIUM:
            self.fields.pop('image_url', None)

    # Define the project model and available form fields
    class Meta:
        model = Project
        fields = ['title', 'description', 'dimensions', 'budget', 'image_url']