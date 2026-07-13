from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from .models import LoginEvent, Profile, Subscription
from .services import consume_ai_generation_credit


class AuthenticationFlowTests(TestCase):
    # Set up a test user before each test
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )

    # Verify that a new user can successfully sign up and profile data is created
    def test_user_can_sign_up(self):
        response = self.client.post(
            reverse('account_signup'),
            {
                'username': 'newuser',
                'first_name': 'New',
                'last_name': 'User',
                'email': 'newuser@example.com',
                'phone_number': '1234567890',
                'address': '10 New Street',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

        user = get_user_model().objects.get(username='newuser')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.phone_number, '1234567890')
        self.assertEqual(profile.address, '10 New Street')

    # Verify that a user can log in using valid username and password
    def test_user_can_log_in_with_username_and_password(self):
        response = self.client.post(
            reverse('account_login'),
            {
                'login': 'tester',
                'password': 'StrongPass123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        event = LoginEvent.objects.first()
        self.assertIsNotNone(event)
        self.assertTrue(event.success)
        self.assertEqual(event.result, LoginEvent.RESULT_SUCCESS)
        self.assertEqual(event.attempted_identifier, 'tester')
        self.assertEqual(event.user, self.user)

    # Verify that a failed login attempt creates a failed login event
    def test_failed_log_in_creates_login_event(self):
        response = self.client.post(
            reverse('account_login'),
            {
                'login': 'tester',
                'password': 'wrong-password',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        event = LoginEvent.objects.first()
        self.assertIsNotNone(event)
        self.assertFalse(event.success)
        self.assertEqual(event.result, LoginEvent.RESULT_FAILED)
        self.assertEqual(event.attempted_identifier, 'tester')

    # Verify that the signup page loads correctly without configured social providers
    def test_signup_page_renders_without_social_apps(self):
        response = self.client.get(reverse('account_signup'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')

    # Verify that an authenticated user can update profile information
    def test_profile_page_allows_updating_phone_and_address(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('edit_profile'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'updated@example.com',
                'phone_number': '1234567890',
                'address': '123 Main Street',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertEqual(self.user.email, 'updated@example.com')

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone_number, '1234567890')
        self.assertEqual(profile.address, '123 Main Street')


class BillingCheckoutTests(TestCase):
    # Set up a user for billing-related tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='billingtester',
            email='billing@example.com',
            password='StrongPass123!',
        )

    @override_settings(
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_PRICE_ID_PREMIUM='5',
        STRIPE_CURRENCY='usd',
        STRIPE_PREMIUM_INTERVAL='month',
    )
    @patch('accounts.views._get_or_create_stripe_customer', return_value='cus_test_123')
    @patch('accounts.views.stripe.checkout.Session.create')
    
    # Verify that checkout creates a Stripe session using numeric price data
    def test_checkout_accepts_numeric_amount_via_price_data(self, mock_create, _mock_customer):
        self.client.force_login(self.user)
        mock_create.return_value = SimpleNamespace(url='https://example.com/checkout')

        response = self.client.post(reverse('start_checkout_session'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://example.com/checkout')

        kwargs = mock_create.call_args.kwargs
        line_item = kwargs['line_items'][0]
        self.assertIn('price_data', line_item)
        self.assertEqual(line_item['price_data']['unit_amount'], 500)
        self.assertEqual(line_item['price_data']['currency'], 'usd')
        self.assertEqual(line_item['price_data']['recurring']['interval'], 'month')

    @override_settings(
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_PRICE_ID_PREMIUM='not_a_price',
    )
    @patch('accounts.views.stripe.checkout.Session.create')
    
    # Verify that checkout rejects an invalid Stripe price configuration
    def test_checkout_rejects_invalid_price_reference(self, mock_create):
        self.client.force_login(self.user)

        response = self.client.post(reverse('start_checkout_session'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('profile'))
        mock_create.assert_not_called()


class SubscriptionAdminControlTests(TestCase):
    # Set up a user for subscription administration tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='premiumadmin',
            email='premiumadmin@example.com',
            password='StrongPass123!',
        )

    # Verify that assigning the Premium plan activates the subscription
    def test_setting_plan_to_premium_marks_subscription_active(self):
        subscription = Subscription.objects.create(user=self.user)
        subscription.plan = Subscription.PLAN_PREMIUM
        subscription.save()

        subscription.refresh_from_db()
        self.assertTrue(subscription.is_active)

    # Verify that Premium subscribers have unlimited AI generation usage
    def test_premium_plan_gets_unlimited_ai_usage(self):
        subscription = Subscription.objects.create(user=self.user, plan=Subscription.PLAN_PREMIUM)
        subscription.ai_usage_count = 999
        subscription.save()

        allowed, _subscription, message = consume_ai_generation_credit(self.user)
        self.assertTrue(allowed)
        self.assertEqual(message, '')


class SubscriptionSuccessSyncTests(TestCase):
    # Set up a user for subscription synchronization tests
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='syncuser',
            email='sync@example.com',
            password='StrongPass123!',
        )

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('accounts.views.stripe.checkout.Session.retrieve')
    # Verify that the success callback synchronizes subscription details from Stripe
    def test_success_view_syncs_premium_status_from_checkout_session(self, mock_session_retrieve):
        self.client.force_login(self.user)
        mock_session_retrieve.return_value = {
            'customer': 'cus_sync_123',
            'subscription': {
                'id': 'sub_sync_123',
                'customer': 'cus_sync_123',
                'status': 'active',
                'current_period_end': 1790000000,
                'items': {
                    'data': [
                        {
                            'price': {
                                'id': 'price_sync_123',
                            }
                        }
                    ]
                },
            },
        }

        response = self.client.get(
            reverse('subscription_success') + '?session_id=cs_test_123',
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.plan, Subscription.PLAN_PREMIUM)
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.stripe_customer_id, 'cus_sync_123')
        self.assertEqual(subscription.stripe_subscription_id, 'sub_sync_123')
