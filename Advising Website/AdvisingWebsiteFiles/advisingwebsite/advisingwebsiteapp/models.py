from django.db import models
from django.contrib.auth.models import UserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from datetime import date, datetime

# Create your models here.

class CustomUserManager(UserManager):
    def _create_user(self, email, first_name, last_name, password, is_student, is_advisor, **extra_fields):
        if not email:
            raise ValueError("You have no provided a valid e-mail address")
    
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, 
                          is_student=is_student, is_advisor=is_advisor, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user
    
    def create_user(self, email=None, first_name=None, last_name=None, password=None, is_student=None, is_advisor=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, first_name, last_name, password, is_student, is_advisor, **extra_fields)
    
    def create_superuser(self, email=None, first_name=None, last_name=None, password=None, is_student=None, is_advisor=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, first_name, last_name, password, is_student, is_advisor, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(blank=True, default='', unique=True)
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')

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
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]