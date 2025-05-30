from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.home, name="home"), #home page route
    path('login/', views.login_view, name='login'), #login page route
    path('register/', views.register, name="register"), #register page route
    path('uploadTranscript/', views.upload_transcript, name="uploadTranscript"), #upload transcript page
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'), #logout returns to home(signed out page)
    path('profile/', views.profile, name='profile'), #profile page route
    path('update_profile/', views.update_profile, name='update_profile'), #Update profile
    path('changePassword/', views.change_password, name='changePassword'), #change password
    path('chat/', views.chathome, name='chatHome'), #chat home
    path('chat/<int:chat_id>/', views.room, name="room"), #chat room
    path('chat/check-membership/<int:chat_id>/', views.check_chat_membership, name='check_chat_membership'), #security measures in chats
    path('error/', views.error_page, name='error_page'),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)), #suppresses 404 for favicon.ico
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)