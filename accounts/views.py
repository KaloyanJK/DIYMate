from allauth.socialaccount.models import SocialApp
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


def home_view(request):
    return render(request, 'home.html')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['login']
            password = form.cleaned_data['password']
            user = User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier)).first()

            if user is not None and user.check_password(password):
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                if form.cleaned_data['remember']:
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)
                return redirect('profile')

            form.add_error(None, 'Invalid username/email or password.')
    else:
        form = LoginForm()

    return render(request, 'account/login.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('profile')
    else:
        form = RegisterForm()

    configured_providers = list(
        SocialApp.objects.filter(provider__in=['google', 'github']).values_list('provider', flat=True)
    )
    return render(request, 'account/signup.html', {'form': form, 'configured_providers': configured_providers})


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')