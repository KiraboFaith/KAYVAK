"""NFR-04: how often does KAYVAK's verdict match the expected verdict?

The "expected" columns are written BY HAND, so right now this is a self-check, not a
comparison with a real technician. To report the 90% honestly, replace or add cases
taken from real technician diagnoses.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from .analysis import analyse

TARGET = 0.90  # NFR-04: at least 90% agreement

# (description, battery, drive, licence_valid, malware, expected overall, expected components)
CASES = [
    ('new laptop, all fine',                95, 98, True,  False, 'Good',     set()),
    ('normal 2-year-old laptop',            78, 90, True,  False, 'Good',     set()),
    ('battery getting weak (R7, R9)',       55, 90, True,  False, 'Warning',  {'Battery'}),
    ('battery nearly dead (about 1 hour)',  30, 90, True,  False, 'Critical', {'Battery'}),
    ('drive wearing out',                   90, 65, True,  False, 'Warning',  {'Storage drive'}),
    ('drive about to fail (R3)',            90, 25, True,  False, 'Critical', {'Storage drive'}),
    ('Windows licence expired (R4)',        90, 90, False, False, 'Warning',  {'Windows licence'}),
    ('virus suspected (R7)',                90, 90, True,  True,  'Critical', {'Security'}),
    ('old battery and old drive',           50, 60, True,  False, 'Warning',  {'Battery', 'Storage drive'}),
    ('weak battery and virus',              55, 90, True,  True,  'Critical', {'Battery', 'Security'}),
    ('everything wrong',                    30, 30, False, True,  'Critical',
        {'Battery', 'Storage drive', 'Windows licence', 'Security'}),
    ('battery exactly at limit is still fine', 60, 70, True, False, 'Good',   set()),
]


def verdict(battery, drive, licence, malware):
    reading = SimpleNamespace(
        battery_health=battery, drive_health=drive,
        licence_valid=licence, suspected_malware=malware,
    )
    report = analyse(reading)
    return report['overall'], {f['component'] for f in report['findings']}


class AccuracyTests(SimpleTestCase):
    def test_agreement_with_expected_verdicts_meets_target(self):
        agreed = 0
        for name, battery, drive, licence, malware, overall, components in CASES:
            got = verdict(battery, drive, licence, malware)
            if got == (overall, components):
                agreed += 1
            else:
                print(f'  DISAGREE: {name}: expected {(overall, components)}, got {got}')
        rate = agreed / len(CASES)
        print(f'\n  Agreement: {agreed}/{len(CASES)} = {rate:.0%} (target {TARGET:.0%})')
        self.assertGreaterEqual(rate, TARGET)