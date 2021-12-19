from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    confirm_email = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Project(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField(auto_now=True)

class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    content = models.TextField()
    status = models.TextField()
    created = models.DateTimeField(auto_now=True)
