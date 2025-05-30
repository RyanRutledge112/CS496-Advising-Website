"""
ASGI config for advisingwebsite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from advisingwebsite.routing import websocket_urlpatterns
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "advisingwebsite.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": (
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        )
    }
)
