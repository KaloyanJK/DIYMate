from datetime import datetime, timezone

from django.conf import settings
from .models import Subscription


ACTIVE_STRIPE_STATUSES = {'active', 'trialing'}


def get_or_create_subscription(user):
    subscription, _ = Subscription.objects.get_or_create(user=user)
    return subscription


def get_free_ai_limit():
    return int(getattr(settings, 'FREE_AI_USAGE_LIMIT', 5))


def consume_ai_generation_credit(user):
    """
    Returns (allowed, subscription, message).
    For premium users, usage is unlimited.
    For free users, usage increments up to FREE_AI_USAGE_LIMIT.
    """
    subscription = get_or_create_subscription(user)

    if subscription.plan == Subscription.PLAN_PREMIUM and subscription.is_active:
        return True, subscription, ''

    free_limit = get_free_ai_limit()
    if subscription.ai_usage_count >= free_limit:
        return False, subscription, (
            f'You have reached your free AI limit ({free_limit}). '
            'Upgrade to Premium for unlimited AI generations.'
        )

    subscription.ai_usage_count += 1
    subscription.save(update_fields=['ai_usage_count', 'updated_at'])
    return True, subscription, ''


def remaining_free_generations(subscription):
    return max(0, get_free_ai_limit() - subscription.ai_usage_count)


def update_subscription_from_stripe_payload(subscription, stripe_subscription):
    status = stripe_subscription.get('status')
    is_active = status in ACTIVE_STRIPE_STATUSES

    current_period_end = stripe_subscription.get('current_period_end')
    renew_date = None
    if current_period_end:
        renew_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)

    price_id = None
    items = stripe_subscription.get('items', {}).get('data', [])
    if items:
        price = items[0].get('price', {})
        price_id = price.get('id')

    subscription.stripe_customer_id = stripe_subscription.get('customer') or subscription.stripe_customer_id
    subscription.stripe_subscription_id = stripe_subscription.get('id')
    subscription.stripe_price_id = price_id
    subscription.is_active = is_active
    subscription.plan = Subscription.PLAN_PREMIUM if is_active else Subscription.PLAN_FREE
    subscription.renew_date = renew_date
    subscription.save()


def mark_subscription_canceled(subscription):
    subscription.is_active = False
    subscription.plan = Subscription.PLAN_FREE
    subscription.renew_date = None
    subscription.save(update_fields=['is_active', 'plan', 'renew_date', 'updated_at'])
