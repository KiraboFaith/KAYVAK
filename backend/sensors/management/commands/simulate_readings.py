import random
import time
from django.core.management.base import BaseCommand
from sensors.models import SensorReading

class Command(BaseCommand):
    help = 'Inserts a simulated sensor reading every few seconds'

    def handle(self, *args, **kwargs):
        statuses = ['Normal', 'Warning', 'Critical']
        while True:
            temp = round(random.uniform(15, 35), 1)
            humidity = round(random.uniform(30, 80), 1)
            status = 'Normal' if temp < 28 else random.choice(statuses)
            SensorReading.objects.create(
                temperature=temp,
                humidity=humidity,
                status=status,
                log_entry=f'Simulated reading: {temp}°C, {humidity}%'
            )
            self.stdout.write(f'Inserted: {temp}°C, {humidity}%, {status}')
            time.sleep(5)