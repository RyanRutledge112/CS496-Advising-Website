from django.contrib import admin
from .models import Post, Category

#Shows Post and Category on admin side of website

admin.site.register(Post)
admin.site.register(Category)