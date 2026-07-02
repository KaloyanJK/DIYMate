# Uses Django’s built-in secure user system
# Automatically:
#     Hashes passwords
#     Validates passwords
#     Prevents weak passwords

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]