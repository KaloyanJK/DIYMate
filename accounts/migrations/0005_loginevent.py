from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_subscription_plan_and_stripe_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_identifier', models.CharField(blank=True, max_length=254)),
                ('result', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed')], max_length=10)),
                ('success', models.BooleanField(default=False)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('full_name_snapshot', models.CharField(blank=True, max_length=150)),
                ('email_snapshot', models.EmailField(blank=True, max_length=254)),
                ('phone_number_snapshot', models.CharField(blank=True, max_length=20)),
                ('address_snapshot', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='login_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
