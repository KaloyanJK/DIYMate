from django.apps import AppConfig


# Configure the Accounts application settings for Django
class AccountsConfig(AppConfig):
    # Define the default primary key type used for models in this app
    default_auto_field = 'django.db.models.BigAutoField'
    # Specify the application name registered with Django
    name = 'accounts'
