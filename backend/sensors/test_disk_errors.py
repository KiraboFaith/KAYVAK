"""How fast a disk's uncorrected read errors are growing."""
from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .disk_trends import disk_error_growth, error_growth
from .models import DiskReading, HealthReading

START = datetime(2026, 11, 1, 12, 0, tzinfo=dt_timezone.utc)


def at(days):
    return START + timedelta(days=days)


def add_sample(days_ago, errors, device_id=0, name='X'):
    """Saves one check (with one disk) as if it happened `days_ago` days ago."""
    stamp = timezone.now() - timedelta(days=days_ago)
    reading = HealthReading.objects.create(battery_health=90, drive_health=90)
    disk = DiskReading.objects.create(
        reading=reading, device_id=device_id, name=name, read_errors_uncorrected=errors)
    DiskReading.objects.filter(pk=disk.pk).update(timestamp=stamp)
    HealthReading.objects.filter(pk=reading.pk).update(timestamp=stamp)
    return HealthReading.objects.get(pk=reading.pk)


class ErrorGrowthTests(SimpleTestCase):
    def test_one_sample_cannot_show_growth(self):
        self.assertIsNone(error_growth([(at(0), 5)]))

    def test_samples_less_than_a_day_apart_say_nothing(self):
        self.assertIsNone(error_growth([(at(0), 5), (at(0.5), 50)]))

    def test_growth_per_day(self):
        result = error_growth([(at(0), 3), (at(1), 9), (at(2), 21)])
        self.assertEqual(result, {'increase': 18, 'days': 2.0, 'per_day': 9.0})

    def test_unchanged_total_is_zero_growth(self):
        result = error_growth([(at(0), 3), (at(3), 3)])
        self.assertEqual(result['increase'], 0)

    def test_empty_values_are_skipped(self):
        result = error_growth([(at(0), None), (at(1), 4), (at(2), 6)])
        self.assertEqual(result['increase'], 2)

    def test_a_counter_reset_is_not_counted_as_negative_growth(self):
        # total fell from 50 to 1: the counter restarted, only the part after it counts
        result = error_growth([(at(0), 50), (at(1), 1), (at(3), 5)])
        self.assertEqual(result, {'increase': 4, 'days': 2.0, 'per_day': 2.0})

    def test_a_reset_with_nothing_after_it_gives_no_answer(self):
        self.assertIsNone(error_growth([(at(0), 50), (at(2), 1)]))


class DiskErrorLookupTests(TestCase):
    """disk_error_growth() reading the saved history from the database."""

    def test_growth_is_found_from_saved_history(self):
        add_sample(3, 2)
        newest = add_sample(0, 12)
        result = disk_error_growth(newest)
        self.assertEqual(result['increase'], 10)
        self.assertEqual(result['name'], 'X')

    def test_history_older_than_the_window_is_ignored(self):
        add_sample(30, 1)
        newest = add_sample(0, 50)
        self.assertIsNone(disk_error_growth(newest))

    def test_growth_on_another_disk_is_not_mixed_in(self):
        add_sample(3, 2, device_id=1, name='Other')
        newest = add_sample(0, 12, device_id=0, name='X')
        self.assertIsNone(disk_error_growth(newest))

    def test_no_history_gives_none(self):
        self.assertIsNone(disk_error_growth(add_sample(0, 3)))

    def test_reading_without_a_database_row_is_fine(self):
        self.assertIsNone(disk_error_growth(SimpleNamespace()))