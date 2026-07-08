from django.contrib import admin
from .models import LoginEvent, Subscription

admin.site.register(Subscription)


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
	list_display = ('created_at', 'attempted_identifier', 'result', 'ip_address', 'user')
	list_filter = ('result', 'created_at')
	search_fields = ('attempted_identifier', 'email_snapshot', 'full_name_snapshot', 'ip_address')