import stripe  # type: ignore[import-not-found]
from decimal import Decimal, InvalidOperation
from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import LoginForm, ProfileForm, RegisterForm
from .models import LoginEvent, Profile, Subscription
from .services import (
    get_free_ai_limit,
    get_or_create_subscription,
    mark_subscription_canceled,
    remaining_free_generations,
    update_subscription_from_stripe_payload,
)


def home_view(request):
    return render(request, 'home.html')


def _get_request_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _record_login_event(request, identifier, user, success):
    profile = None
    if user:
        profile = Profile.objects.filter(user=user).first()

    LoginEvent.objects.create(
        user=user,
        attempted_identifier=identifier,
        result=LoginEvent.RESULT_SUCCESS if success else LoginEvent.RESULT_FAILED,
        success=success,
        ip_address=_get_request_ip(request),
        full_name_snapshot=(user.get_full_name().strip() if user else ''),
        email_snapshot=(user.email if user else ''),
        phone_number_snapshot=(profile.phone_number if profile else ''),
        address_snapshot=(profile.address if profile else ''),
    )


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['login']
            password = form.cleaned_data['password']
            user = User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier)).first()

            if user is not None and user.check_password(password):
                _record_login_event(request, identifier, user, True)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                if form.cleaned_data['remember']:
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)
                return redirect('profile')

            _record_login_event(request, identifier, user, False)
            form.add_error(None, 'Invalid username/email or password.')
        else:
            _record_login_event(request, request.POST.get('login', '').strip(), None, False)
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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    subscription = get_or_create_subscription(request.user)
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'subscription': subscription,
        'free_ai_limit': get_free_ai_limit(),
        'remaining_free_generations': remaining_free_generations(subscription),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required
def edit_profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, user=request.user, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(user=request.user, instance=profile)

    return render(request, 'accounts/edit_profile.html', {'form': form, 'profile': profile})


def _validate_stripe_configuration():
    if not settings.STRIPE_SECRET_KEY:
        return 'Stripe secret key is missing. Set STRIPE_SECRET_KEY.'
    if not settings.STRIPE_PRICE_ID_PREMIUM:
        return 'Premium price id is missing. Set STRIPE_PRICE_ID_PREMIUM.'
    return ''


def _build_checkout_line_item():
    price_reference = (settings.STRIPE_PRICE_ID_PREMIUM or '').strip()

    if price_reference.startswith('price_'):
        return {'price': price_reference, 'quantity': 1}, ''

    try:
        amount = Decimal(price_reference)
    except InvalidOperation:
        return None, (
            'STRIPE_PRICE_ID_PREMIUM must be a Stripe price id (price_...) '
            'or a numeric amount like 9.99.'
        )

    if amount <= 0:
        return None, 'STRIPE_PRICE_ID_PREMIUM numeric fallback must be greater than 0.'

    amount_in_cents = int((amount * 100).to_integral_value())
    currency = getattr(settings, 'STRIPE_CURRENCY', 'usd').lower()
    interval = getattr(settings, 'STRIPE_PREMIUM_INTERVAL', 'month')
    if interval not in {'day', 'week', 'month', 'year'}:
        interval = 'month'

    return {
        'price_data': {
            'currency': currency,
            'unit_amount': amount_in_cents,
            'product_data': {'name': 'DIYMate Premium'},
            'recurring': {'interval': interval},
        },
        'quantity': 1,
    }, ''


def _format_currency(amount, currency):
    symbols = {
        'gbp': '£',
        'usd': '$',
        'eur': '€',
    }
    symbol = symbols.get(currency.lower(), f'{currency.upper()} ')
    return f'{symbol}{amount:.2f}'


def _get_billing_display_context():
    price_reference = (settings.STRIPE_PRICE_ID_PREMIUM or '').strip()
    currency = getattr(settings, 'STRIPE_CURRENCY', 'usd').lower()
    interval = getattr(settings, 'STRIPE_PREMIUM_INTERVAL', 'month')
    if interval not in {'day', 'week', 'month', 'year'}:
        interval = 'month'

    if price_reference.startswith('price_'):
        return {
            'price_label': 'Configured in Stripe Dashboard',
            'price_reference': price_reference,
            'currency': currency.upper(),
            'interval': interval,
        }

    try:
        amount = Decimal(price_reference)
    except InvalidOperation:
        return {
            'price_label': 'Not configured',
            'price_reference': price_reference,
            'currency': currency.upper(),
            'interval': interval,
        }

    return {
        'price_label': _format_currency(amount, currency),
        'price_reference': price_reference,
        'currency': currency.upper(),
        'interval': interval,
    }


def _get_or_create_stripe_customer(subscription):
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    customer = stripe.Customer.create(
        email=subscription.user.email,
        name=subscription.user.get_full_name() or subscription.user.username,
        metadata={'user_id': str(subscription.user_id)},
    )
    subscription.stripe_customer_id = customer['id']
    subscription.save(update_fields=['stripe_customer_id', 'updated_at'])
    return customer['id']


@login_required
def billing_info_view(request):
    subscription = get_or_create_subscription(request.user)
    pricing = _get_billing_display_context()
    return render(request, 'accounts/billing_info.html', {
        'subscription': subscription,
        'pricing': pricing,
        'free_ai_limit': get_free_ai_limit(),
        'remaining_free_generations': remaining_free_generations(subscription),
    })


@login_required
def start_checkout_session(request):
    if request.method != 'POST':
        return redirect('profile')

    configuration_error = _validate_stripe_configuration()
    if configuration_error:
        messages.error(request, configuration_error)
        return redirect('profile')

    line_item, line_item_error = _build_checkout_line_item()
    if line_item_error:
        messages.error(request, line_item_error)
        return redirect('profile')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = get_or_create_subscription(request.user)

    if subscription.plan == Subscription.PLAN_PREMIUM and subscription.is_active:
        messages.info(request, 'You already have an active Premium subscription.')
        return redirect('profile')

    customer_id = _get_or_create_stripe_customer(subscription)
    try:
        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            customer=customer_id,
            line_items=[line_item],
            success_url=request.build_absolute_uri(reverse('subscription_success')),
            cancel_url=request.build_absolute_uri(reverse('subscription_cancel')),
            client_reference_id=str(request.user.id),
            metadata={'user_id': str(request.user.id)},
            subscription_data={'metadata': {'user_id': str(request.user.id)}},
        )
    except stripe.error.StripeError as exc:
        messages.error(request, exc.user_message or 'Unable to start Stripe checkout right now.')
        return redirect('profile')

    return redirect(checkout_session.url, permanent=False)


@login_required
def billing_portal(request):
    if request.method != 'POST':
        return redirect('profile')

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Stripe secret key is missing. Set STRIPE_SECRET_KEY.')
        return redirect('profile')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = get_or_create_subscription(request.user)

    if not subscription.stripe_customer_id:
        messages.error(request, 'No Stripe customer found yet. Upgrade first to create one.')
        return redirect('profile')

    portal_session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=request.build_absolute_uri(reverse('profile')),
    )
    return redirect(portal_session.url, permanent=False)


@login_required
def subscription_success(request):
    messages.success(request, 'Payment completed. Your Premium access is being activated.')
    return redirect('profile')


@login_required
def subscription_cancel(request):
    messages.info(request, 'Checkout canceled. You are still on the Free plan.')
    return redirect('profile')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    if not settings.STRIPE_SECRET_KEY or not endpoint_secret:
        return HttpResponse(status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, signature, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    event_type = event.get('type')
    data_object = event.get('data', {}).get('object', {})

    if event_type == 'checkout.session.completed':
        customer_id = data_object.get('customer')
        subscription_id = data_object.get('subscription')
        user_id = data_object.get('metadata', {}).get('user_id') or data_object.get('client_reference_id')

        subscription = None
        if user_id:
            try:
                subscription, _ = Subscription.objects.get_or_create(user_id=int(user_id))
            except (TypeError, ValueError):
                subscription = None
        elif customer_id:
            subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

        if subscription:
            subscription.stripe_customer_id = customer_id or subscription.stripe_customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.save(update_fields=['stripe_customer_id', 'stripe_subscription_id', 'updated_at'])

            if subscription_id:
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                update_subscription_from_stripe_payload(subscription, stripe_subscription)

    if event_type in {'customer.subscription.created', 'customer.subscription.updated'}:
        stripe_subscription = data_object
        customer_id = stripe_subscription.get('customer')
        metadata_user_id = stripe_subscription.get('metadata', {}).get('user_id')

        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not subscription and metadata_user_id:
            try:
                subscription, _ = Subscription.objects.get_or_create(user_id=int(metadata_user_id))
            except (TypeError, ValueError):
                subscription = None

        if subscription:
            update_subscription_from_stripe_payload(subscription, stripe_subscription)

    if event_type == 'customer.subscription.deleted':
        customer_id = data_object.get('customer')
        stripe_subscription_id = data_object.get('id')
        subscription = Subscription.objects.filter(
            stripe_customer_id=customer_id,
            stripe_subscription_id=stripe_subscription_id,
        ).first()
        if subscription:
            mark_subscription_canceled(subscription)

    return JsonResponse({'status': 'ok'})