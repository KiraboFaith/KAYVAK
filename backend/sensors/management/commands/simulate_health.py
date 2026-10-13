import random
import time
from django.core.management.base import BaseCommand
from sensors.models import HealthReading


class Command(BaseCommand):
    help = 'Inserts a simulated laptop health reading every 5 seconds'

    def handle(self, *args, **kwargs):
        while True:
            reading = HealthReading.objects.create(
                battery_health=round(random.uniform(30, 100), 1),
                drive_health=round(random.uniform(30, 100), 1),
                licence_valid=random.random() > 0.2,
                suspected_malware=random.random() > 0.85,
            )
            self.stdout.write(f'Inserted: {reading}')
            time.sleep(5)