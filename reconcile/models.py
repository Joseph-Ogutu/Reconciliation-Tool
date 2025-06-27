
from django.db import models
from django.contrib.auth.models import User

class Reconciliation(models.Model):
    internal_file = models.FileField(upload_to='uploads/internal/')
    provider_file = models.FileField(upload_to='uploads/provider/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    last_reconciled = models.DateTimeField(null=True, blank=True)
    schedule_frequency = models.CharField(max_length=50, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], null=True, blank=True)

    def __str__(self):
        return f"Reconciliation {self.id} - {self.uploaded_at}"