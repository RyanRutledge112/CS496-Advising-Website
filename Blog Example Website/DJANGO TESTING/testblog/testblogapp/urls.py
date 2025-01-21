from django.urls import path
#from . import views
from .views import HomeView, ArticleDetailView, AddPostView, UpdatePostView, DeletePostView, AddCategoryView, CategoryView, AddCommentView, EditCommentView, DeleteCommentView

#Creates urls for the website to use

urlpatterns = [
    #path('', views.home, name="home"),
    path('', HomeView.as_view(), name="home"),
    path('article/<int:pk>', ArticleDetailView.as_view(), name="article-details"),
    path('add_post/', AddPostView.as_view(), name ='add_post'),
    path('article/edit/<int:pk>', UpdatePostView.as_view(), name = 'update_post'),
    path('article/<int:pk>/remove', DeletePostView.as_view(), name = 'delete_post'),
    path('add_category/', AddCategoryView.as_view(), name ='add_category'),
    path('category/<str:cats>/', CategoryView, name='category'),
    path('article/<int:pk>/comment/', AddCommentView.as_view(), name='add_comment'),
    path('comment/edit/<int:pk>/', EditCommentView.as_view(), name='edit_comment'),
    path('comment/delete/<int:pk>/', DeleteCommentView.as_view(), name='delete_comment'),
]