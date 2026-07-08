from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='account_login'),
    path('signup/', views.signup_view, name='account_signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('billing/checkout/', views.start_checkout_session, name='start_checkout_session'),
    path('billing/portal/', views.billing_portal, name='billing_portal'),
    path('billing/success/', views.subscription_success, name='subscription_success'),
    path('billing/cancel/', views.subscription_cancel, name='subscription_cancel'),
    path('billing/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
