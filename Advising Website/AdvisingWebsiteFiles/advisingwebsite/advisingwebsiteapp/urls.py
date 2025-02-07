from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('login/', views.login_view, name='login'), #login page route
    path('register/', views.register, name="register"), #register page route
    path('features/', views.features, name="features"), #features page route
    path('messages/', views.messages, name="messages"), #messages page route
    path('uploadTranscript/', views.upload_transcript, name="uploadTranscript"), #upload transcript page
]
