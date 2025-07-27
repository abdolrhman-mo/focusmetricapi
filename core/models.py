import uuid
from django.db import models
from django.contrib.auth.models import User

class Reason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reasons')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.description

class FocusEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='focus_entries')
    date = models.DateField()
    hours = models.FloatField(null=True, blank=True)
    reason = models.ForeignKey(Reason, on_delete=models.SET_NULL, null=True, blank=True, related_name='focus_entries')

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{str(self.user.username)} - {str(self.date)}" 