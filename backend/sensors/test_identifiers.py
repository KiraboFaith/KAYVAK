import json
import os
import tempfile

from django.test import SimpleTestCase

from .identifiers import (
    battery_identity_from_xml, collect_snapshot, disks_from_json, displays_from_json,
    hash_serial, ram_from_json, windows_from_json,
)


class HashSerialTests(SimpleTestCase):
    def test_same_serial_gives_same_fingerprint_and_hides_the_serial(self):
        first = hash_serial('S3Z9NB0K123456')
        self.assertEqual(first, hash_serial('s3z9nb0k123456  '))   # case and spaces do not matter
        self.assertNotIn('123456', first)
        self.assertEqual(len(first), 16)

    def test_different_serials_give_different_fingerprints(self):
        self.assertNotEqual(hash_serial('AAA111'), hash_serial('AAA112'))

    def test_empty_and_placeholder_serials_give_none(self):
        for value in (None, '', '   ', '00000000', 'To Be Filled By O.E.M.', 'Default string', 'Unknown'):
            self.assertIsNone(hash_serial(value), value)

    def test_trailing_dot_on_nvme_serials_is_ignored(self):
        self.assertEqual(hash_serial('0025_388A_1234.'), hash_serial('0025_388A_1234'))


class ParserTests(SimpleTestCase):
    def test_disks(self):
        text = json.dumps([
            {'Model': 'TOSHIBA MQ04ABF100', 'Serial': 'X1', 'MediaType': 'HDD', 'Size': 1000204886016},
            {'Model': 'BC511 NVMe', 'Serial': None, 'MediaType': 'SSD', 'Size': 256060514304},
        ])
        disks = disks_from_json(text)
        self.assertEqual(disks[0]['size_gb'], 1000)
        self.assertEqual(disks[1]['size_gb'], 256)
        self.assertIsNotNone(disks[0]['serial_hash'])
        self.assertIsNone(disks[1]['serial_hash'])

    def test_single_object_instead_of_a_list(self):
        one = json.dumps({'Model': 'X', 'Serial': 'S', 'MediaType': 'SSD', 'Size': 500107862016})
        self.assertEqual(len(disks_from_json(one)), 1)

    def test_ram_capacity_is_in_gb_and_blank_serial_is_none(self):
        text = json.dumps([
            {'Slot': 'DIMM A', 'Manufacturer': 'Samsung', 'PartNumber': 'M471A2K43DB1-CTD ',
             'Serial': '00000000', 'Capacity': 17179869184},
        ])
        stick = ram_from_json(text)[0]
        self.assertEqual(stick['capacity_gb'], 16)
        self.assertEqual(stick['part_number'], 'M471A2K43DB1-CTD')
        self.assertIsNone(stick['serial_hash'])

    def test_display(self):
        text = json.dumps([{'Manufacturer': 'AUO', 'Product': '2B6D', 'Serial': '0', 'Year': 2020}])
        screen = displays_from_json(text)[0]
        self.assertEqual((screen['manufacturer'], screen['year']), ('AUO', 2020))

    def test_windows(self):
        info = windows_from_json('{"InstallDate":"2026-01-15T09:30:12","Version":"10.0.26100","Build":"26100"}')
        self.assertEqual(info['install_date'], '2026-01-15T09:30:12')


class BatteryIdentityTests(SimpleTestCase):
    def write(self, body):
        handle, path = tempfile.mkstemp(suffix='.xml')
        with os.fdopen(handle, 'w') as f:
            f.write(
                '<BatteryReport xmlns="http://schemas.microsoft.com/battery/2012"><Batteries Count="1">'
                f'<Battery>{body}</Battery></Batteries></BatteryReport>'
            )
        self.addCleanup(os.remove, path)
        return path

    def test_battery_identity(self):
        path = self.write(
            '<Id>DELL 1234</Id><Manufacturer>SMP</Manufacturer><SerialNumber>ABC123</SerialNumber>'
            '<ManufactureDate>2021-05-03</ManufactureDate><DesignCapacity>42000</DesignCapacity>'
            '<CycleCount>412</CycleCount>'
        )
        battery = battery_identity_from_xml(path)
        self.assertEqual(battery['cycle_count'], 412)
        self.assertEqual(battery['design_capacity'], 42000)
        self.assertEqual(battery['manufacture_date'], '2021-05-03')
        self.assertIsNotNone(battery['serial_hash'])

    def test_no_battery_in_report_gives_none(self):
        handle, path = tempfile.mkstemp(suffix='.xml')
        with os.fdopen(handle, 'w') as f:
            f.write('<BatteryReport><Batteries Count="0"/></BatteryReport>')
        self.addCleanup(os.remove, path)
        self.assertIsNone(battery_identity_from_xml(path))


class CollectSnapshotTests(SimpleTestCase):
    def test_everything_is_read_and_a_failure_is_not_hidden(self):
        def run(script):
            if 'Win32_PhysicalMemory' in script:
                raise RuntimeError('access denied')
            if 'Get-PhysicalDisk' in script:
                return '[{"Model":"X","Serial":"S","MediaType":"SSD","Size":500107862016}]'
            if 'WmiMonitorID' in script:
                return '[]'
            return '{"InstallDate":"2026-01-15T09:30:12","Version":"10.0","Build":"26100"}'

        def battery_report():
            raise RuntimeError('no battery')

        data = collect_snapshot(run, battery_report)
        self.assertEqual(len(data['disks']), 1)
        self.assertIsNone(data['ram'])            # failed: saved as "not checked"
        self.assertIsNone(data['battery'])
        self.assertEqual(data['display'], [])     # a laptop with no screen data is not an error
        self.assertIn('access denied', data['errors']['ram'])
        self.assertEqual(data['windows']['build'], '26100')