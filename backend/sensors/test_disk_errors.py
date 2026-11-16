"""How fast a disk's uncorrected read errors are growing, and what analyse() does with it."""
from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .analysis import analyse
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


class DiskErrorFindingTests(TestCase):
    """analyse() with real saved disk history."""

    def drive_findings(self, reading):
        return [f for f in analyse(reading)['findings'] if f['component'] == 'Storage drive']

    def test_growing_errors_are_critical(self):
        add_sample(3, 2)
        newest = add_sample(0, 12)
        (finding,) = self.drive_findings(newest)
        self.assertEqual(finding['status'], 'Critical')
        self.assertIn('10 were added in the last 3 days', finding['evidence'])

    def test_old_errors_that_stopped_growing_stay_a_warning(self):
        add_sample(5, 3)
        newest = add_sample(0, 3)
        (finding,) = self.drive_findings(newest)
        self.assertEqual(finding['status'], 'Warning')
        self.assertIn('None were added in the last 5 days', finding['evidence'])

    def test_no_history_is_still_a_warning_and_does_not_claim_growth(self):
        newest = add_sample(0, 3)
        (finding,) = self.drive_findings(newest)
        self.assertEqual(finding['status'], 'Warning')
        self.assertNotIn('added', finding['evidence'])

    def test_growth_replaces_the_health_score_finding_instead_of_doubling_it(self):
        add_sample(4, 1)
        newest = add_sample(0, 9)
        newest.drive_health = 60          # the health score alone would say Warning
        findings = self.drive_findings(newest)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['status'], 'Critical')

    def test_growth_finding_still_never_calls_for_a_major_repair(self):
        add_sample(3, 2)
        newest = add_sample(0, 12)
        (finding,) = self.drive_findings(newest)
        self.assertEqual(finding['repair'], 'Minor repair')