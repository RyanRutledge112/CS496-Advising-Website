from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to the Django User model
    content = models.TextField()  # Text content of the post
    image = models.ImageField(upload_to='posts/', blank=True, null=True)  # Optional image
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the post is created

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"