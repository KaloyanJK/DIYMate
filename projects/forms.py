from django import forms
from accounts.services import get_or_create_subscription

from .models import Project


class ProjectForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user is None:
            return

        subscription = get_or_create_subscription(user)
        if subscription.plan != subscription.PLAN_PREMIUM:
            self.fields.pop('image_url', None)

    class Meta:
        model = Project
        fields = ['title', 'description', 'dimensions', 'budget', 'image_url']