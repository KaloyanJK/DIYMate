from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    login = forms.CharField(label="Username or email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    remember = forms.BooleanField(label="Remember me", required=False)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")

        return email
