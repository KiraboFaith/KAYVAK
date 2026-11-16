import random
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from sensors.models import HealthReading


def clamp(value, low=20.0, high=100.0):
    return max(low, min(high, value))


class Command(BaseCommand):
    help = 'Inserts a simulated laptop health reading every 5 seconds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--history', type=int, default=0, metavar='DAYS',
            help='first add one made-up reading per past day, so the trend lines have '
                 'something to show (trends need readings from at least 5 different days)')

    def seed_history(self, days):
        """One simulated reading for each of the last `days` days, wearing out slowly."""
        now = timezone.now()
        battery, drive = random.uniform(88, 96), random.uniform(88, 96)
        for ago in range(days, 0, -1):
            battery = clamp(battery - random.uniform(0.2, 1.2))
            drive = clamp(drive - random.uniform(0.1, 0.8))
            reading = HealthReading.objects.create(
                battery_health=round(battery, 1), drive_health=round(drive, 1))
            # created_at-style fields are set automatically, so move it into the past afterwards
            HealthReading.objects.filter(pk=reading.pk).update(
                timestamp=now - timedelta(days=ago))
        self.stdout.write(f'Added {days} days of simulated history.')
        return battery, drive

    def handle(self, *args, **options):
        # Start from a healthy laptop, then let the numbers drift slowly,
        # like real wear, so the demo can move from Good to Warning to Critical.
        battery = random.uniform(80, 100)
        drive = random.uniform(80, 100)
        if options['history'] > 0:
            battery, drive = self.seed_history(options['history'])
        licence_valid = True
        suspected_malware = False

        while True:
            battery = clamp(battery + random.uniform(-7, 3))
            drive = clamp(drive + random.uniform(-6, 3))

            # Rare events, so the page does not flicker between problems
            if random.random() < 0.04:
                licence_valid = not licence_valid
            if suspected_malware:
                suspected_malware = random.random() > 0.3      # usually clears soon
            else:
                suspected_malware = random.random() < 0.03     # rarely starts

            # Sometimes the laptop is "serviced": battery and drive jump back up
            if battery < 30 and drive < 30:
                battery, drive = random.uniform(85, 100), random.uniform(85, 100)

            reading = HealthReading.objects.create(
                battery_health=round(battery, 1),
                drive_health=round(drive, 1),
                licence_valid=licence_valid,
                suspected_malware=suspected_malware,
            )
            self.stdout.write(f'Inserted: {reading}')
            time.sleep(5)