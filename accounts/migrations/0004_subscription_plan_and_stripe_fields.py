import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='plan',
            field=models.CharField(
                choices=[('free', 'Free'), ('premium', 'Premium')],
                default='free',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='subscription',
            name='stripe_price_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
