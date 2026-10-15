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
    
class HealthReading(models.Model):
    battery_health = models.FloatField()   # % of original capacity
    drive_health = models.FloatField()     # % of drive life remaining
    licence_valid = models.BooleanField(default=True)
    suspected_malware = models.BooleanField(default=False)
    source = models.CharField(max_length=20, default='simulated')
    licence_checked = models.BooleanField(default=True)   # False = Windows would not tell us
    malware_checked = models.BooleanField(default=True)   # False = Defender could not be read
    check_seconds = models.FloatField(null=True, blank=True)  # how long the whole check took
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: battery {self.battery_health}%, drive {self.drive_health}%"   