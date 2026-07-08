from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Subscription
from planner.models import AIPlan
from .models import Project


class ProjectDetailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )
        self.project = Project.objects.create(
            user=self.user,
            title='Garden Shed',
            description='A small shed',
            dimensions='4x6',
            budget='500',
        )

    def test_project_detail_shows_ai_plan_when_available(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards', 'Screws'],
            steps=['Measure the area', 'Install the frame'],
            cost='120.50',
            safety='Wear gloves',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('project_detail', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Generated Plans')
        self.assertContains(response, 'Wood boards')
        self.assertContains(response, 'Measure the area')

    def test_delete_project_page_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('delete_project', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Project')

    def test_generating_plan_replaces_existing_plan_for_project(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Old boards'],
            steps=['Old step'],
            cost='10.00',
            safety='Old safety',
        )

        fake_response = type('Response', (), {
            'choices': [type('Choice', (), {'message': type('Message', (), {'content': '{"materials": ["New boards"], "steps": ["New step"], "cost": 25, "safety": "New safety"}'})()})()]
        })()

        self.client.force_login(self.user)
        with patch('planner.views.client.chat.completions.create', return_value=fake_response):
            response = self.client.get(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        plans = AIPlan.objects.filter(project=self.project)
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.first().materials, ['New boards'])
        self.assertEqual(plans.first().steps, ['New step'])
        self.assertEqual(plans.first().cost, 25)
        self.assertEqual(plans.first().safety, 'New safety')

    def test_create_project_generates_plan_and_redirects_to_detail(self):
        fake_response = type('Response', (), {
            'choices': [type('Choice', (), {'message': type('Message', (), {'content': '{"materials": ["New boards"], "steps": ["New step"], "cost": 30, "safety": "Use care"}'})()})()]
        })()

        self.client.force_login(self.user)
        with patch('projects.views.client.chat.completions.create', return_value=fake_response):
            response = self.client.post(reverse('create_project'), {
                'title': 'New Project',
                'description': 'A new project',
                'dimensions': '8x10',
                'budget': '600',
            })

        project = Project.objects.get(title='New Project')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_detail', kwargs={'pk': project.pk}))
        plans = AIPlan.objects.filter(project=project)
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.first().materials, ['New boards'])

    def test_edit_project_generates_new_plan_and_redirects_to_detail(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Old boards'],
            steps=['Old step'],
            cost='10.00',
            safety='Old safety',
        )

        fake_response = type('Response', (), {
            'choices': [type('Choice', (), {'message': type('Message', (), {'content': '{"materials": ["Updated boards"], "steps": ["Updated step"], "cost": 45, "safety": "Updated safety"}'})()})()]
        })()

        self.client.force_login(self.user)
        with patch('projects.views.client.chat.completions.create', return_value=fake_response):
            response = self.client.post(reverse('edit_project', kwargs={'pk': self.project.pk}), {
                'title': 'Garden Shed',
                'description': 'Updated description',
                'dimensions': '4x6',
                'budget': '500',
            })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_detail', kwargs={'pk': self.project.pk}))
        plans = AIPlan.objects.filter(project=self.project)
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.first().materials, ['Updated boards'])
        self.assertEqual(plans.first().steps, ['Updated step'])

    def test_create_project_normalizes_generated_steps(self):
        fake_response = type('Response', (), {
            'choices': [type('Choice', (), {'message': type('Message', (), {'content': '{"materials": ["Boards"], "steps": ["1.1 Measure the area", "2.2 Cut the boards"], "cost": 20, "safety": "Use care"}'})()})()]
        })()

        self.client.force_login(self.user)
        with patch('projects.views.client.chat.completions.create', return_value=fake_response):
            response = self.client.post(reverse('create_project'), {
                'title': 'Normalized Project',
                'description': 'A test project',
                'dimensions': '4x6',
                'budget': '300',
            })

        project = Project.objects.get(title='Normalized Project')
        self.assertEqual(response.status_code, 302)
        plan = AIPlan.objects.get(project=project)
        self.assertEqual(plan.steps, ['Measure the area', 'Cut the boards'])

    def test_free_user_at_limit_cannot_generate_plan(self):
        Subscription.objects.create(
            user=self.user,
            plan=Subscription.PLAN_FREE,
            is_active=False,
            ai_usage_count=settings.FREE_AI_USAGE_LIMIT,
        )

        self.client.force_login(self.user)
        with patch('planner.views.client.chat.completions.create') as mocked_create:
            response = self.client.get(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_detail', kwargs={'pk': self.project.pk}))
        mocked_create.assert_not_called()

    def test_premium_user_has_unlimited_generate_plan_access(self):
        Subscription.objects.create(
            user=self.user,
            plan=Subscription.PLAN_PREMIUM,
            is_active=True,
            ai_usage_count=10_000,
        )
        fake_response = type('Response', (), {
            'choices': [type('Choice', (), {'message': type('Message', (), {'content': '{"materials": ["Premium boards"], "steps": ["Do premium step"], "cost": 55, "safety": "Premium safety"}'})()})()]
        })()

        self.client.force_login(self.user)
        with patch('planner.views.client.chat.completions.create', return_value=fake_response):
            response = self.client.get(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AIPlan.objects.filter(project=self.project).exists())


class ProjectListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123!',
        )
        self.project = Project.objects.create(
            user=self.user,
            title='Garden Shed',
            description='A small shed',
            dimensions='4x6',
            budget='500',
        )

    def test_project_list_shows_latest_ai_plan_preview(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards', 'Screws'],
            steps=['Measure the area', 'Install the frame'],
            cost='120.50',
            safety='Wear gloves',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('project_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Latest AI Plan')
        self.assertContains(response, 'Wood boards')
