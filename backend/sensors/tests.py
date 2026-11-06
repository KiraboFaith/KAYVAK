from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient as _APIClient

from .analysis import analyse, trend
from .models import DiskReading, HealthReading


def APIClient():
    """A test client that sends the same header the dashboard sends."""
    return _APIClient(HTTP_X_KAYVAK_CLIENT='dashboard')



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
        
class DriveHealthTests(SimpleTestCase):
    """Commit 2: a hard drive's Wear 0 must not turn into "100% healthy"."""

    def pct(self, text):
        from sensors.management.commands.collect_windows import drive_percent_from_json
        return drive_percent_from_json(text)

    HDD = '{"Name":"TOSHIBA","MediaType":"HDD","Health":"%s","Wear":%s}'
    SSD = '{"Name":"BC511","MediaType":"SSD","Health":"%s","Wear":%s}'

    def test_hdd_wear_zero_and_healthy_word_is_not_measured(self):
        self.assertIsNone(self.pct('[' + self.HDD % ('Healthy', 0) + ']'))

    def test_ssd_wear_is_used(self):
        self.assertEqual(self.pct('[' + self.SSD % ('Healthy', 5) + ']'), 95.0)

    def test_hdd_wear_is_ignored_but_ssd_wear_is_used_on_the_same_laptop(self):
        text = '[' + self.HDD % ('Healthy', 0) + ',' + self.SSD % ('Healthy', 12) + ']'
        self.assertEqual(self.pct(text), 88.0)

    def test_warning_word_is_still_a_real_signal_on_an_hdd(self):
        self.assertEqual(self.pct('[' + self.HDD % ('Warning', 'null') + ']'), 60.0)

    def test_unhealthy_word_wins_over_good_wear(self):
        text = '[' + self.HDD % ('Unhealthy', 0) + ',' + self.SSD % ('Healthy', 3) + ']'
        self.assertEqual(self.pct(text), 20.0)

    def test_single_disk_object_is_handled(self):
        self.assertIsNone(self.pct(self.HDD % ('Healthy', 0)))

    def test_no_disks_at_all_is_an_error(self):
        with self.assertRaises(RuntimeError):
            self.pct('[]')

    def test_unmeasured_drive_gives_no_finding(self):
        report = analyse(make_reading(drive=None))
        self.assertIsNone(find(report, 'Storage drive'))


class UnmeasuredDriveEndpointTests(TestCase):
    def test_unmeasured_drive_is_listed_as_unchecked_not_as_good(self):
        HealthReading.objects.create(battery_health=90, drive_health=None, source='windows')
        data = APIClient().get('/api/sensors/health/').data
        self.assertIsNone(data['measurements']['drive_health'])
        self.assertIn('Storage drive', data['unchecked'])
        self.assertIsNone(data['trends']['drive'])
        
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
            'read_disk_details': mock.Mock(return_value=[]),
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
        
class DiskDetailTests(TestCase):
    SAMPLE = (
        '[{"DeviceId":0,"Name":"TOSHIBA MQ04ABF100","MediaType":"HDD","Health":"Healthy",'
        '"Temperature":34,"PowerOnHours":4389,"LoadUnload":34980,"ReadErrors":0,'
        '"ReadUncorrected":null,"Wear":0},'
        '{"DeviceId":1,"Name":"BC511 NVMe SK hynix 256GB","MediaType":"SSD","Health":"Healthy",'
        '"Temperature":46,"PowerOnHours":null,"LoadUnload":null,"ReadErrors":null,'
        '"ReadUncorrected":null,"Wear":0}]'
    )

    def test_json_is_turned_into_one_dictionary_per_disk(self):
        from sensors.management.commands.collect_windows import disk_details_from_json
        disks = disk_details_from_json(self.SAMPLE)
        self.assertEqual(len(disks), 2)
        self.assertEqual(disks[0]['power_on_hours'], 4389)
        self.assertEqual(disks[0]['load_unload_cycles'], 34980)
        self.assertIsNone(disks[1]['power_on_hours'])   # not reported stays None

    def test_a_single_disk_is_handled(self):
        from sensors.management.commands.collect_windows import disk_details_from_json
        one = '{"DeviceId":0,"Name":"X","MediaType":"SSD","Health":"Healthy","Temperature":30}'
        self.assertEqual(len(disk_details_from_json(one)), 1)

    def test_collector_saves_disks_and_survives_a_disk_failure(self):
        from unittest import mock
        from sensors.management.commands import collect_windows as cw
        command = cw.Command()
        command.stdout = mock.Mock()
        command.stderr = mock.Mock()
        reads = {
            'read_battery': mock.Mock(return_value=80.0),
            'read_drive': mock.Mock(return_value=90.0),
            'read_licence': mock.Mock(return_value=True),
            'read_malware': mock.Mock(return_value=False),
            'read_disk_details': mock.Mock(return_value=cw.disk_details_from_json(self.SAMPLE)),
        }
        with mock.patch.multiple(cw, **reads):
            command.collect_once()
        self.assertEqual(DiskReading.objects.count(), 2)
        self.assertEqual(DiskReading.objects.get(device_id=0).reading, HealthReading.objects.first())

        reads['read_disk_details'] = mock.Mock(side_effect=RuntimeError('no access'))
        with mock.patch.multiple(cw, **reads):
            command.collect_once()
        self.assertEqual(HealthReading.objects.count(), 2)   # main reading still saved
        self.assertEqual(DiskReading.objects.count(), 2)     # no new disk rows
        
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
        
class AlertDecisionTests(SimpleTestCase):
    def test_off_never_alerts(self):
        from .notify import decide_alert
        self.assertEqual(decide_alert(False, {'Battery'}, set()), (False, set()))

    def test_new_urgent_problem_alerts_once(self):
        from .notify import decide_alert
        alert, seen = decide_alert(True, {'Battery'}, set())
        self.assertTrue(alert)
        self.assertFalse(decide_alert(True, {'Battery'}, seen)[0])

    def test_second_new_problem_alerts_again(self):
        from .notify import decide_alert
        self.assertTrue(decide_alert(True, {'Battery', 'Security'}, {'Battery'})[0])

    def test_problem_that_goes_away_and_returns_alerts_again(self):
        from .notify import decide_alert
        _, seen = decide_alert(True, {'Battery'}, set())
        _, seen = decide_alert(True, set(), seen)
        self.assertTrue(decide_alert(True, {'Battery'}, seen)[0])

    def test_turning_on_later_alerts_for_a_problem_already_there(self):
        from .notify import decide_alert
        _, seen = decide_alert(False, {'Battery'}, set())
        self.assertTrue(decide_alert(True, {'Battery'}, seen)[0])

    def test_only_critical_is_urgent(self):
        from .notify import urgent_findings
        report = analyse(make_reading(battery=55, drive=30))  # battery Warning, drive Critical
        self.assertEqual([f['component'] for f in urgent_findings(report)], ['Storage drive'])


class CollectorAlertTests(TestCase):
    def setUp(self):
        from sensors.management.commands import collect_windows as cw
        self.command = cw.Command()

    def run_check(self, battery=80.0, enabled=True):
        from unittest import mock
        from sensors.management.commands import collect_windows as cw
        from .models import NotificationSetting
        setting = NotificationSetting.current()
        setting.enabled = enabled
        setting.save()
        self.command.stdout, self.command.stderr = mock.Mock(), mock.Mock()
        reads = {
            'read_battery': mock.Mock(return_value=battery),
            'read_drive': mock.Mock(return_value=90.0),
            'read_licence': mock.Mock(return_value=True),
            'read_malware': mock.Mock(return_value=False),
        }
        with mock.patch.multiple(cw, **reads), mock.patch.object(cw, 'show_windows_toast') as toast:
            self.command.collect_once()
        return toast

    def test_healthy_laptop_shows_no_alert(self):
        self.assertFalse(self.run_check(battery=80).called)

    def test_critical_battery_shows_one_alert_and_not_a_repeat(self):
        self.assertEqual(self.run_check(battery=30).call_count, 1)
        self.assertFalse(self.run_check(battery=30).called)

    def test_alert_text_has_explanation_and_advice(self):
        title, body = self.run_check(battery=30).call_args[0]
        self.assertIn('KAYVAK', title)
        self.assertIn('Battery', body)
        self.assertIn('technician', body)

    def test_notifications_off_shows_nothing(self):
        self.assertFalse(self.run_check(battery=30, enabled=False).called)

    def test_a_failing_popup_does_not_stop_the_check(self):
        from unittest import mock
        from sensors.management.commands import collect_windows as cw
        from .models import NotificationSetting
        NotificationSetting.objects.update_or_create(pk=1, defaults={'enabled': True})
        self.command.stdout, self.command.stderr = mock.Mock(), mock.Mock()
        reads = {'read_battery': mock.Mock(return_value=30.0), 'read_drive': mock.Mock(return_value=90.0),
                 'read_licence': mock.Mock(return_value=True), 'read_malware': mock.Mock(return_value=False)}
        with mock.patch.object(cw, 'show_windows_toast', side_effect=RuntimeError('blocked')), \
             mock.patch.multiple(cw, **reads):
            self.command.collect_once()
        self.assertEqual(HealthReading.objects.count(), 1)        
        
        
class DatasetComparisonTests(TestCase):
    url = '/api/sensors/dataset/'
    POINTS = list(range(0, 101, 5))

    def make_summary_file(self):
        import json
        import tempfile
        healthy = [float(i * 100) for i in range(21)]      # 0, 100, ... 2000
        summary = {
            'source': 'Backblaze Drive Stats', 'models': ['TEST MODEL'],
            'date_from': '2025-10-01', 'date_to': '2025-12-31',
            'healthy_drives': 100, 'failed_drives': 5, 'points': self.POINTS,
            'metrics': {'power_on_hours': {'healthy': healthy, 'failed': [v + 500 for v in healthy]}},
        }
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(summary, handle)
        handle.close()
        return handle.name

    def test_percentile_rank(self):
        from sensors.dataset import percentile_rank
        q = [float(i * 100) for i in range(21)]
        self.assertEqual(percentile_rank(-5, self.POINTS, q), 0.0)
        self.assertEqual(percentile_rank(5000, self.POINTS, q), 100.0)
        self.assertEqual(percentile_rank(1000, self.POINTS, q), 50.0)
        self.assertEqual(percentile_rank(150, self.POINTS, q), 7.5)

    def test_404_when_there_is_no_summary_file(self):
        from unittest import mock
        with mock.patch('sensors.dataset.SUMMARY_PATH', '/no/such/file.json'):
            self.assertEqual(APIClient().get(self.url).status_code, 404)

    def test_hard_drive_is_compared_and_ssd_is_not(self):
        from unittest import mock
        reading = HealthReading.objects.create(battery_health=90, drive_health=None, source='windows')
        DiskReading.objects.create(reading=reading, device_id=0, name='TOSHIBA', media_type='HDD',
                                   power_on_hours=1000, temperature=34)
        DiskReading.objects.create(reading=reading, device_id=1, name='SK hynix', media_type='SSD',
                                   power_on_hours=None, temperature=46)
        with mock.patch('sensors.dataset.SUMMARY_PATH', self.make_summary_file()):
            data = APIClient().get(self.url).data
        hdd, ssd = data['drives']
        metric = hdd['metrics'][0]
        self.assertEqual(metric['key'], 'power_on_hours')
        self.assertEqual(metric['percentile'], 50.0)
        self.assertEqual(metric['healthy_median'], 1000.0)
        self.assertEqual(metric['failed_median'], 1500.0)
        self.assertEqual(len(hdd['metrics']), 1)   # temperature is not in this test summary
        self.assertEqual(ssd['metrics'], [])
        self.assertIn('hard drives', ssd['note'])
        self.assertEqual(data['dataset']['healthy_drives'], 100)

    def test_no_disk_rows_gives_an_empty_list(self):
        from unittest import mock
        with mock.patch('sensors.dataset.SUMMARY_PATH', self.make_summary_file()):
            self.assertEqual(APIClient().get(self.url).data['drives'], [])
            
class ServerProtectionTests(TestCase):
    url = '/api/sensors/health/'

    def test_request_without_header_is_refused(self):
        self.assertEqual(_APIClient().get(self.url).status_code, 403)

    def test_request_with_wrong_header_is_refused(self):
        client = _APIClient(HTTP_X_KAYVAK_CLIENT='something-else')
        self.assertEqual(client.get(self.url).status_code, 403)

    def test_request_with_header_gets_past_the_check(self):
        # 404 is fine here: there is no data yet, but the request was allowed in.
        self.assertNotEqual(APIClient().get(self.url).status_code, 403)

    def test_unknown_host_is_refused(self):
        client = APIClient()
        self.assertEqual(client.get(self.url, HTTP_HOST='evil.example.com').status_code, 400)