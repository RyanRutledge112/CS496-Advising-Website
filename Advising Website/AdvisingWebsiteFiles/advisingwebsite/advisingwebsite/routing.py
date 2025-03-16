from django.urls import path, re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from advisingwebsite.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<chat_id>\w+)/$", ChatConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})