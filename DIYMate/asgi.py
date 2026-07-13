"""
ASGI config for DIYMate project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application


# Set the default Django settings module for the ASGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DIYMate.settings')
# Create the ASGI application used by the web server
application = get_asgi_application()
