from django.urls import path
from . import views

urlpatterns = [
    path('feed/', views.feed, name='feed'),
    path('post/create/', views.create_post, name='post_create'),
]