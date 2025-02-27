from django.contrib import admin
from .models import User, Chat, ChatMember, Message, Degree, DegreeCourse, Course, Prerequisites, UserDegree

# Register your models here.

admin.site.register(User)
admin.site.register(Chat)
admin.site.register(ChatMember)
admin.site.register(Message)
admin.site.register(Degree)
admin.site.register(DegreeCourse)
admin.site.register(Course)
admin.site.register(Prerequisites)
admin.site.register(UserDegree)