from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('HR', 'HR Department'),
        ('OE', 'OE Department'),
        ('SPINNING', 'Spinning Department'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='OE')

    def __str__(self):
        return f"{self.username} ({self.role})"