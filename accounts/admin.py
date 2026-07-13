from django.contrib import admin
from .models import LoginEvent, Subscription


# Register the Subscription model in the Django admin panel
admin.site.register(Subscription)

@admin.register(LoginEvent)
# Customize the Django admin interface for login event records
class LoginEventAdmin(admin.ModelAdmin):
    # Display important login event details in the admin list view
	list_display = ('created_at', 'attempted_identifier', 'result', 'ip_address', 'user')
 	# Add filters to help administrators find login events quickly
	list_filter = ('result', 'created_at')
	# Enable searching login events by user and security-related fields
	search_fields = ('attempted_identifier', 'email_snapshot', 'full_name_snapshot', 'ip_address')