from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import datetime, date

#Creates the models that will be added to the database for use by the website.

class Category(models.Model):
        name = models.CharField(max_length=255)
      
        def __str__(self):
            return self.name
    
        def get_absolute_url(self):
            return reverse('home')

class Post(models.Model):
    title = models.CharField(max_length=255)
    title_tag = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    post_date = models.DateField(auto_now_add=True)
    category = models.CharField(max_length=255)
    

    def __str__(self):
        return self.title + ' | ' + str(self.author)
    
    def get_absolute_url(self):
        return reverse('home')
    
class Comment(models.Model):
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.author} - {self.body[:20]}'

    def get_absolute_url(self):
        return reverse('article-details', args=[str(self.post.id)])