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
    battery_cycles = models.IntegerField(null=True, blank=True)  # charge cycles; None = not reported
    drive_health = models.FloatField(null=True, blank=True)  # % of drive life left; None = not measured
    licence_valid = models.BooleanField(default=True)
    suspected_malware = models.BooleanField(default=False)
    source = models.CharField(max_length=20, default='simulated')
    licence_checked = models.BooleanField(default=True)   # False = Windows would not tell us
    malware_checked = models.BooleanField(default=True)   # False = Defender could not be read
    check_seconds = models.FloatField(null=True, blank=True)  # how long the whole check took
    charge_percent = models.FloatField(null=True, blank=True)  # battery charge right now; None = not reported
    charging = models.BooleanField(null=True, blank=True)      # True = on charger; None = not reported
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: battery {self.battery_health}%, drive {self.drive_health}%"
    
class DiskReading(models.Model):
    """The raw numbers one physical disk gave during one check (for early-warning trends)."""
    reading = models.ForeignKey(HealthReading, on_delete=models.CASCADE, related_name='disks')
    device_id = models.IntegerField()                        # Windows disk number (0, 1, ...)
    name = models.CharField(max_length=100)                  # e.g. "TOSHIBA MQ04ABF100"
    media_type = models.CharField(max_length=20, blank=True) # HDD, SSD or Unspecified
    health_status = models.CharField(max_length=20, blank=True)
    # Every number below is empty (None) when Windows does not report it for that disk.
    temperature = models.FloatField(null=True, blank=True)   # degrees C
    power_on_hours = models.IntegerField(null=True, blank=True)
    load_unload_cycles = models.IntegerField(null=True, blank=True)  # hard drives only
    read_errors_total = models.IntegerField(null=True, blank=True)
    read_errors_uncorrected = models.IntegerField(null=True, blank=True)
    wear = models.FloatField(null=True, blank=True)          # % used, as Windows reports it
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: disk {self.device_id} ({self.name})"


class NotificationSetting(models.Model):
    """The owner's notification choice. There is only ever one row (pk=1)."""
    enabled = models.BooleanField(default=False)  # True = send urgent alerts
    asked = models.BooleanField(default=False)    # True once the owner has answered the first-open question
    email_enabled = models.BooleanField(default=False)  # True = the owner agreed to alerts by email
    updated = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls):
        setting, _ = cls.objects.get_or_create(pk=1)
        return setting

    def __str__(self):
        return f"notifications {'on' if self.enabled else 'off'}"
    


class Snapshot(models.Model):
    """One scan of the laptop's parts, saved so a later scan can be compared with it."""
    label = models.CharField(max_length=60)      # e.g. "before" or "after"
    created = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()                    # see identifiers.collect_snapshot

    class Meta:
        ordering = ['-created', '-id']           # newest first

    def __str__(self):
        return f'{self.label} ({self.created:%Y-%m-%d %H:%M})'
    
class QueuedEmail(models.Model):
    """An email that could not be sent (no internet). It is sent later."""
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created', 'id']

    def __str__(self):
        return f'{self.subject} (waiting since {self.created:%Y-%m-%d %H:%M})'