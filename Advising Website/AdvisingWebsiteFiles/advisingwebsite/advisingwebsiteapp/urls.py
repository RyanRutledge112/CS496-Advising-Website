from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.login_view, name='login'), #login page route
    path('register/', views.register, name="register"), #register page route
    path('messages/', views.messages, name="messages"), #messages page route
    path('send_message/', views.send_message, name="send_message"),
    path('uploadTranscript/', views.upload_transcript, name="uploadTranscript"), #upload transcript page
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'), #logout returns to home(signed out page)
    path('profile/', views.profile, name='profile'), #profle page route
    path('update_profile/', views.update_profile, name='update_profile'), #Update profile
    path('changePassword/', views.change_password, name='changePassword'), #change password
    path('chat', views.index, name='index'), #testing purposes
    path('chat/<str:room_name>/', views.room, name="room"), #chat room
]
