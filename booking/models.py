from django.db import models
from django.utils import timezone
from app.models import Customer, Personnel, Work  # استفاده از مدل‌های موجود

class Appointment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.end_time and hasattr(self.work, 'duration'):
            self.end_time = self.start_time + timezone.timedelta(minutes=self.work.duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - {self.work.work_name} ({self.start_time})"