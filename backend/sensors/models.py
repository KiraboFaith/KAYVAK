from django.db import models


class SensorReading(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    status = models.CharField(max_length=50)
    log_entry = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: {self.temperature}°C, {self.humidity}%, {self.status}"