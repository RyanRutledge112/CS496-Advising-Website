from django.db import models
from django.contrib.auth.models import UserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from datetime import date, datetime

# Create your models here. Autoincremented id functions are created for every class, so there is no need to
# explicitly write any code that makes a primary key with an autoincrementing id.

class CustomUserManager(UserManager):
    def _create_user(self, email, first_name, last_name, password, is_student, is_advisor, student_id, **extra_fields):
        if not email:
            raise ValueError("You have no provided a valid e-mail address")
    
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, 
                          is_student=is_student, is_advisor=is_advisor, student_id=student_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user
    
    def create_user(self, email=None, first_name=None, last_name=None, password=None, is_student=None, is_advisor=None, student_id=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, first_name, last_name, password, is_student, is_advisor, student_id=student_id, **extra_fields)
    
    def create_superuser(self, email=None, first_name=None, last_name=None, password=None, is_student=None, is_advisor=None, student_id=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, first_name, last_name, password, is_student, is_advisor, student_id=student_id, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(blank=True, default='', unique=True)
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')
    student_id = models.IntegerField(unique=True, null=True)

    is_student = models.BooleanField(default=True)
    is_advisor = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email.split('@')[0]
    
    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]
    
    def get_student_id(self):
        return self.student_id
    
class Chat(models.Model):
    chat_name = models.CharField(max_length=255)

    def __str__(self):
        return self.chat_name
    def last_30_messages(self):
        return self.chat_messages.order_by('-date_sent')[:30]
    def last_message(self):
        last_msg = self.chat_messages.order_by('-date_sent').first()
        return last_msg if last_msg else None

class ChatMember(models.Model):
    user = models.ForeignKey(User, related_name="joined_chats", on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, related_name='members',on_delete=models.CASCADE)
    chat_last_viewed = models.DateTimeField(auto_now_add=True)
    chat_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f'User: {self.user.get_full_name()} | Chat: {self.chat.__str__()}'.strip()

class Message(models.Model):
    sent_by_member = models.ForeignKey(ChatMember, related_name="messages", on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, related_name="chat_messages", on_delete=models.CASCADE)
    message_content = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sent_by_member} | {self.message_content}'.strip()

#You can add more degree types if needed
class Degree(models.Model):
    DEGREE_TYPE_CHOICES = [
        (1, "Major"),
        (2, "Minor"),
        (3, "Certificate"),
    ]

    degree_name = models.CharField(max_length=255)
    degree_number = models.CharField(max_length=255)
    concentration = models.CharField(max_length=255)
    hours_needed = models.IntegerField()
    degree_type = models.IntegerField(choices=DEGREE_TYPE_CHOICES)

    def __str__(self):
        degree_type_display = dict(self.DEGREE_TYPE_CHOICES).get(self.degree_type, "Unknown")
        return f"{self.degree_name} {self.concentration} {degree_type_display}".strip()

class Course(models.Model):
    course_name = models.CharField(max_length=255)
    hours = models.IntegerField()
    is_colonade = models.BooleanField()
    colonade_id = models.CharField(max_length=255, null=True)
    
    corequisites = models.TextField(null=True, blank=True)
    restrictions = models.TextField(null=True, blank=True)
    recent_terms = models.TextField(null=True, blank=True)

    def __str__(self):
        result = f'Name: {self.course_name}\nHours required to graduate: {self.hours} hours'
        if self.is_colonade:
            result += f'\nColonade requirement for: {self.colonade_id}'
        return result.strip()
class DegreeCourse(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    is_elective = models.BooleanField()
    is_required = models.BooleanField()
    group_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        desc = f'{self.course.course_name}'
        if self.is_elective and self.is_required:
            desc += f' is an elective and a requirement for {self.degree.degree_name}'
        elif self.is_elective:
            desc += f' is an elective for {self.degree.degree_name}'
        elif self.is_required:
            desc += f' is a requirement for {self.degree.degree_name}'
        return desc

class Prerequisites(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="prerequisites")
    prerequisite = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="required_for")

    def __str__(self):
        return f"{self.prerequisite.course_name} is a prerequisite for {self.course.course_name}"
    
class UserDegree(models.Model):
    user_student_id = models.ForeignKey(User, on_delete=models.CASCADE)
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)

    def __str__(self):
        return f"Student {self.user_student_id.get_full_name} with a student id of {self.user_student_id.student_id} is going for a degree in {self.degree.__str__}".strip()