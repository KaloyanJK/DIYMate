from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class LoginForm(forms.Form):
    login = forms.CharField(label="Username or email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    remember = forms.BooleanField(label="Remember me", required=False)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30, label="First name")
    last_name = forms.CharField(required=True, max_length=30, label="Last name")
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True, max_length=20, label="Phone number")
    address = forms.CharField(required=True, max_length=255, label="Address")

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "address",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name', '').strip()
        user.last_name = self.cleaned_data.get('last_name', '').strip()

        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number': self.cleaned_data.get('phone_number', ''),
                    'address': self.cleaned_data.get('address', ''),
                },
            )

        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, max_length=30)
    last_name = forms.CharField(required=False, max_length=30)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['phone_number', 'address']
        labels = {
            'phone_number': 'Phone Number',
            'address': 'Address',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.email = self.cleaned_data.get('email', '')
            self.user.save(update_fields=['first_name', 'last_name', 'email'])
            profile.user = self.user
        if commit:
            profile.save()
        return profile
