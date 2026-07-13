from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Subscription
from planner.models import AIPlan
from .forms import ProjectForm
from .models import Project


class ProjectDetailTests(TestCase):
    # Set up a test user and project before each project detail test
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

    # Verify that the project detail page displays an existing AI-generated plan
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

    # Verify that the delete project confirmation page loads correctly
    def test_delete_project_page_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('delete_project', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Project')

    # Verify that generating a new AI plan replaces the previous project plan
    def test_generating_plan_replaces_existing_plan_for_project(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Old boards'],
            steps=['Old step'],
            cost='10.00',
            safety='Old safety',
        )

        fake_output = '{"materials": ["New boards"], "steps": ["New step"], "cost": 25, "safety": "New safety"}'

        self.client.force_login(self.user)
        with patch('planner.views.generate_plan_text', return_value=fake_output):
            response = self.client.post(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        plans = AIPlan.objects.filter(project=self.project)
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.first().materials, ['New boards'])
        self.assertEqual(plans.first().steps, ['New step'])
        self.assertEqual(plans.first().cost, 25)
        self.assertEqual(plans.first().safety, 'New safety')

    # Verify that creating a project does not automatically generate an AI plan
    def test_create_project_saves_without_generating_plan(self):
        self.client.force_login(self.user)
        with patch('projects.views.generate_plan_text') as mocked_generate:
            response = self.client.post(reverse('create_project'), {
                'title': 'New Project',
                'description': 'A new project',
                'dimensions': '8x10',
                'budget': '600',
            })

        project = Project.objects.get(title='New Project')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_detail', kwargs={'pk': project.pk}))
        self.assertFalse(AIPlan.objects.filter(project=project).exists())
        mocked_generate.assert_not_called()

    # Verify that editing a project does not regenerate the existing AI plan
    def test_edit_project_saves_without_regenerating_plan(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Old boards'],
            steps=['Old step'],
            cost='10.00',
            safety='Old safety',
        )

        self.client.force_login(self.user)
        with patch('projects.views.generate_plan_text') as mocked_generate:
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
        self.assertEqual(plans.first().materials, ['Old boards'])
        self.assertEqual(plans.first().steps, ['Old step'])
        mocked_generate.assert_not_called()

    # Verify that creating a project does not create an AI plan by default
    def test_create_project_does_not_create_plan(self):
        self.client.force_login(self.user)
        with patch('projects.views.generate_plan_text') as mocked_generate:
            response = self.client.post(reverse('create_project'), {
                'title': 'Normalized Project',
                'description': 'A test project',
                'dimensions': '4x6',
                'budget': '300',
            })

        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title='Normalized Project')
        self.assertFalse(AIPlan.objects.filter(project=project).exists())
        mocked_generate.assert_not_called()

    # Verify that free users cannot access the image URL field in the project form
    def test_free_user_form_hides_image_url_field(self):
        form = ProjectForm(user=self.user)

        self.assertNotIn('image_url', form.fields)

    # Verify that free users cannot submit or save an image URL
    def test_free_user_cannot_submit_image_url(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('create_project'), {
            'title': 'Image Restricted Project',
            'description': 'A test project',
            'dimensions': '4x6',
            'budget': '300',
            'image_url': 'https://example.com/should-not-save.png',
        })

        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title='Image Restricted Project')
        self.assertIsNone(project.image_url)

    # Verify that free users do not see the AI drawing generation option
    def test_free_user_does_not_see_generate_drawing_button(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards'],
            steps=['Measure area'],
            cost='90.00',
            safety='Wear gloves',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('project_detail', kwargs={'pk': self.project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Generate Drawing')

    # Verify that free users who reach the AI usage limit cannot generate more plans
    def test_free_user_at_limit_cannot_generate_plan(self):
        Subscription.objects.create(
            user=self.user,
            plan=Subscription.PLAN_FREE,
            is_active=False,
            ai_usage_count=settings.FREE_AI_USAGE_LIMIT,
        )

        self.client.force_login(self.user)
        with patch('planner.views.generate_plan_text') as mocked_generate:
            response = self.client.post(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('project_detail', kwargs={'pk': self.project.pk}))
        mocked_generate.assert_not_called()

    # Verify that Premium users can generate unlimited AI plans
    def test_premium_user_has_unlimited_generate_plan_access(self):
        Subscription.objects.create(
            user=self.user,
            plan=Subscription.PLAN_PREMIUM,
            is_active=True,
            ai_usage_count=10_000,
        )
        fake_output = '{"materials": ["Premium boards"], "steps": ["Do premium step"], "cost": 55, "safety": "Premium safety"}'

        self.client.force_login(self.user)
        with patch('planner.views.generate_plan_text', return_value=fake_output):
            response = self.client.post(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AIPlan.objects.filter(project=self.project).exists())

    # Verify that AI plan generation stores a temporary drawing preview
    def test_generate_plan_stores_temporary_drawing_preview(self):
        fake_output = '{"materials": ["Boards"], "steps": ["Step 1"], "cost": 40, "safety": "Use goggles"}'

        self.client.force_login(self.user)
        with patch('planner.views.generate_plan_text', return_value=fake_output):
            with patch('planner.views.generate_drawing_preview', return_value=('https://example.com/blueprint.png', 'drawing prompt')):
                response = self.client.post(reverse('generate_plan', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        plan = AIPlan.objects.get(project=self.project)
        self.assertEqual(plan.temporary_drawing_data, 'https://example.com/blueprint.png')

    # Verify that saving a drawing moves it from temporary storage to permanent storage
    def test_save_drawing_moves_temporary_to_permanent(self):
        AIPlan.objects.create(
            project=self.project,
            materials=['Wood boards'],
            steps=['Measure area'],
            cost='90.00',
            safety='Wear gloves',
            temporary_drawing_data='https://example.com/temp-drawing.png',
        )

        self.client.force_login(self.user)
        response = self.client.post(reverse('save_plan_drawing', kwargs={'project_id': self.project.pk}))

        self.assertEqual(response.status_code, 302)
        plan = AIPlan.objects.get(project=self.project)
        self.assertIsNone(plan.temporary_drawing_data)
        self.assertEqual(plan.saved_drawing_data, 'https://example.com/temp-drawing.png')


class ProjectListTests(TestCase):
    # Set up a test user and project before each project list test
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

    # Verify that the project list displays the latest AI plan preview
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
