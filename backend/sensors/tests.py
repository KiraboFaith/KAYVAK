from types import SimpleNamespace

from django.test import SimpleTestCase

from .analysis import analyse


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