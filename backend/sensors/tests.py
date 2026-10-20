from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .analysis import analyse, trend
from .models import HealthReading



def make_reading(battery=90, drive=90, licence=True, malware=False):
    """A fake reading with the same fields as HealthReading (no database needed)."""
    return SimpleNamespace(
        battery_health=battery,
        drive_health=drive,
        licence_valid=licence,
        suspected_malware=malware,
    )


def find(report, component):
    for f in report['findings']:
        if f['component'] == component:
            return f
    return None


class AnalyseTests(SimpleTestCase):
    def test_healthy_laptop_is_good(self):
        report = analyse(make_reading())
        self.assertEqual(report['overall'], 'Good')
        self.assertEqual(report['findings'], [])

    def test_battery_warning(self):
        report = analyse(make_reading(battery=55))
        self.assertEqual(find(report, 'Battery')['status'], 'Warning')
        self.assertEqual(report['overall'], 'Warning')

    def test_battery_critical(self):
        report = analyse(make_reading(battery=35))
        self.assertEqual(find(report, 'Battery')['status'], 'Critical')
        self.assertEqual(report['overall'], 'Critical')

    def test_battery_limits(self):
        # exactly 60 is still Good, exactly 40 is Warning (not Critical)
        self.assertIsNone(find(analyse(make_reading(battery=60)), 'Battery'))
        self.assertEqual(find(analyse(make_reading(battery=40)), 'Battery')['status'], 'Warning')

    def test_drive_warning_and_critical(self):
        self.assertEqual(find(analyse(make_reading(drive=65)), 'Storage drive')['status'], 'Warning')
        self.assertEqual(find(analyse(make_reading(drive=30)), 'Storage drive')['status'], 'Critical')

    def test_invalid_licence_is_software_warning(self):
        finding = find(analyse(make_reading(licence=False)), 'Windows licence')
        self.assertEqual(finding['status'], 'Warning')
        self.assertEqual(finding['type'], 'software')

    def test_malware_is_critical(self):
        report = analyse(make_reading(malware=True))
        self.assertEqual(find(report, 'Security')['status'], 'Critical')
        self.assertEqual(report['overall'], 'Critical')

    def test_overall_is_the_worst_finding(self):
        report = analyse(make_reading(battery=55, malware=True))
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(report['overall'], 'Critical')

    def test_every_finding_has_explanation_evidence_and_advice(self):
        report = analyse(make_reading(battery=30, drive=30, licence=False, malware=True))
        self.assertEqual(len(report['findings']), 4)
        for f in report['findings']:
            for key in ('explanation', 'evidence', 'advice', 'type'):
                self.assertTrue(f[key])
class TrendTests(SimpleTestCase):
    def test_too_few_readings_gives_no_trend(self):
        self.assertIsNone(trend([90, 89, 88], 60, 40))

    def test_falling_battery_predicts_checks_to_limits(self):
        # drops 2 per check, now at 80: 10 checks to reach 60, 20 to reach 40
        result = trend([88, 86, 84, 82, 80], 60, 40)
        self.assertEqual(result['direction'], 'falling')
        self.assertEqual(result['change_per_check'], -2.0)
        self.assertEqual(result['checks_to_warning'], 10)
        self.assertEqual(result['checks_to_critical'], 20)

    def test_flat_readings_are_stable_with_no_prediction(self):
        result = trend([90, 90, 90, 90, 90], 60, 40)
        self.assertEqual(result['direction'], 'stable')
        self.assertIsNone(result['checks_to_warning'])

    def test_rising_readings_never_predict_failure(self):
        result = trend([70, 75, 80, 85, 90], 60, 40)
        self.assertEqual(result['direction'], 'rising')
        self.assertIsNone(result['checks_to_critical'])

    def test_already_below_limit_is_zero(self):
        result = trend([70, 65, 55, 50, 45], 60, 40)
        self.assertEqual(result['checks_to_warning'], 0)
        self.assertGreater(result['checks_to_critical'], 0)
class HealthEndpointTests(TestCase):
    url = '/api/sensors/health/'

    def test_404_when_no_readings(self):
        self.assertEqual(APIClient().get(self.url).status_code, 404)

    def test_report_includes_trends_once_enough_history_exists(self):
        for battery in (88, 86, 84, 82, 80):
            HealthReading.objects.create(battery_health=battery, drive_health=95)
        data = APIClient().get(self.url).data
        self.assertEqual(data['trends']['battery']['direction'], 'falling')
        self.assertEqual(data['trends']['drive']['direction'], 'stable')

    def test_trends_are_none_with_little_history(self):
        HealthReading.objects.create(battery_health=90, drive_health=90)
        data = APIClient().get(self.url).data
        self.assertIsNone(data['trends']['battery'])        
    
    def test_report_says_where_the_reading_came_from(self):
        HealthReading.objects.create(battery_health=90, drive_health=90, source='windows')
        self.assertEqual(APIClient().get(self.url).data['source'], 'windows')

    def test_source_defaults_to_simulated(self):
        HealthReading.objects.create(battery_health=90, drive_health=90)
        self.assertEqual(APIClient().get(self.url).data['source'], 'simulated')
    
    def test_unchecked_items_are_listed(self):
        HealthReading.objects.create(
            battery_health=90, drive_health=90, source='windows',
            licence_checked=False, malware_checked=False, check_seconds=4.2,
        )
        data = APIClient().get(self.url).data
        self.assertEqual(data['unchecked'], ['Windows licence', 'Security'])
        self.assertEqual(data['check_seconds'], 4.2)

    def test_nothing_unchecked_by_default(self):
        HealthReading.objects.create(battery_health=90, drive_health=90)
        self.assertEqual(APIClient().get(self.url).data['unchecked'], [])


class CollectorTests(TestCase):
    """Runs the collector with fake Windows answers, so it works on any computer."""

    def run_once(self, licence=True, malware=False):
        from unittest import mock
        from sensors.management.commands import collect_windows as cw
        command = cw.Command()
        command.stdout = mock.Mock()
        command.stderr = mock.Mock()
        reads = {
            'read_battery': mock.Mock(return_value=80.0),
            'read_drive': mock.Mock(return_value=90.0),
            'read_licence': licence if callable(licence) else mock.Mock(return_value=licence),
            'read_malware': malware if callable(malware) else mock.Mock(return_value=malware),
        }
        with mock.patch.multiple(cw, **reads):
            command.collect_once()
        return HealthReading.objects.first()

    def test_normal_check_is_saved_as_windows_and_timed(self):
        reading = self.run_once()
        self.assertEqual(reading.source, 'windows')
        self.assertTrue(reading.licence_checked and reading.malware_checked)
        self.assertIsNotNone(reading.check_seconds)

    def test_unreadable_licence_is_marked_not_checked(self):
        def broken():
            raise RuntimeError('no access')
        reading = self.run_once(licence=broken)
        self.assertFalse(reading.licence_checked)
        self.assertTrue(reading.malware_checked)
        
class NotificationSettingTests(TestCase):
    url = '/api/sensors/notifications/'

    def test_default_is_off_and_not_asked(self):
        data = APIClient().get(self.url).data
        self.assertEqual(data, {'enabled': False, 'asked': False})

    def test_owner_can_turn_it_on_and_it_is_remembered(self):
        client = APIClient()
        response = client.post(self.url, {'enabled': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get(self.url).data, {'enabled': True, 'asked': True})

    def test_saying_no_counts_as_asked(self):
        client = APIClient()
        client.post(self.url, {'enabled': False}, format='json')
        self.assertEqual(client.get(self.url).data, {'enabled': False, 'asked': True})

    def test_owner_can_turn_it_on_later(self):
        client = APIClient()
        client.post(self.url, {'enabled': False}, format='json')
        client.post(self.url, {'enabled': True}, format='json')
        self.assertTrue(client.get(self.url).data['enabled'])

    def test_bad_value_is_rejected(self):
        response = APIClient().post(self.url, {'enabled': 'yes'}, format='json')
        self.assertEqual(response.status_code, 400)