import copy

from django.test import SimpleTestCase

from .comparison import compare


def laptop():
    """A snapshot of a laptop, shaped like identifiers.collect_snapshot builds."""
    return {
        'disks': [
            {'model': 'TOSHIBA MQ04ABF100', 'media_type': 'HDD', 'size_gb': 1000, 'serial_hash': 'aaaa'},
            {'model': 'BC511 NVMe', 'media_type': 'SSD', 'size_gb': 256, 'serial_hash': 'bbbb'},
        ],
        'ram': [
            {'slot': 'DIMM A', 'manufacturer': 'Samsung', 'part_number': 'M471', 'capacity_gb': 8, 'serial_hash': 'r1'},
            {'slot': 'DIMM B', 'manufacturer': 'Samsung', 'part_number': 'M471', 'capacity_gb': 8, 'serial_hash': 'r2'},
        ],
        'battery': {'name': 'DELL 1234', 'manufacturer': 'SMP', 'manufacture_date': '2021-05-03',
                    'design_capacity': 42000, 'cycle_count': 412, 'serial_hash': 'bat1'},
        'display': [{'manufacturer': 'AUO', 'product_code': '2B6D', 'year': 2020, 'serial_hash': None}],
        'windows': {'install_date': '2026-01-15T09:30:12', 'version': '10.0.26100', 'build': '26100'},
    }


def statuses(result):
    return {c['component']: c['status'] for c in result['components']}


class NothingChangedTests(SimpleTestCase):
    def test_the_same_laptop_twice_flags_nothing(self):
        result = compare(laptop(), laptop())
        self.assertEqual(result['changed'], [])
        self.assertEqual(result['not_checked'], [])

    def test_normal_use_between_scans_is_not_a_change(self):
        after = laptop()
        after['battery']['cycle_count'] = 415            # the laptop was charged a few times
        after['windows']['build'] = '26200'              # Windows updated
        result = compare(laptop(), after)
        self.assertEqual(result['changed'], [])


class SwapOnePartTests(SimpleTestCase):
    """The "done when" of Step 3: swap one part and only that part is flagged."""

    def test_swapping_a_ram_stick_flags_only_the_ram(self):
        after = laptop()
        after['ram'][1] = {'slot': 'DIMM B', 'manufacturer': 'Kingston', 'part_number': 'KVR',
                           'capacity_gb': 4, 'serial_hash': 'r9'}
        result = compare(laptop(), after)
        self.assertEqual(result['changed'], ['Memory (RAM)'])
        ram = next(c for c in result['components'] if c['component'] == 'Memory (RAM)')
        self.assertEqual(sorted(i['state'] for i in ram['items']), ['added', 'removed', 'unchanged'])
        self.assertIn('went down', ram['notes'][0])      # 16 GB to 12 GB

    def test_swapping_a_drive_flags_only_the_drive(self):
        after = laptop()
        after['disks'][1] = {'model': 'WD Blue SN570', 'media_type': 'SSD', 'size_gb': 500, 'serial_hash': 'cccc'}
        self.assertEqual(compare(laptop(), after)['changed'], ['Storage drive'])

    def test_a_new_battery_is_caught_by_its_serial_and_its_cycle_count(self):
        after = laptop()
        after['battery'] = dict(after['battery'], serial_hash='bat2', cycle_count=3)
        result = compare(laptop(), after)
        self.assertEqual(result['changed'], ['Battery'])

    def test_a_battery_called_new_but_with_many_cycles_is_called_out(self):
        after = laptop()
        after['battery'] = dict(after['battery'], serial_hash='bat2', cycle_count=350)
        battery = next(c for c in compare(laptop(), after)['components'] if c['component'] == 'Battery')
        self.assertEqual(battery['status'], 'changed')
        self.assertIn('350 charge cycles', battery['notes'][0])

    def test_battery_without_serial_is_caught_when_cycles_drop(self):
        before, after = laptop(), laptop()
        before['battery']['serial_hash'] = after['battery']['serial_hash'] = None
        after['battery']['cycle_count'] = 2
        self.assertEqual(compare(before, after)['changed'], ['Battery'])

    def test_battery_without_serial_and_rising_cycles_cannot_be_judged(self):
        before, after = laptop(), laptop()
        before['battery']['serial_hash'] = after['battery']['serial_hash'] = None
        after['battery']['cycle_count'] = 420
        result = compare(before, after)
        self.assertEqual(statuses(result)['Battery'], 'not_checked')

    def test_reinstalling_windows_flags_only_windows(self):
        after = laptop()
        after['windows']['install_date'] = '2026-11-08T14:00:00'
        self.assertEqual(compare(laptop(), after)['changed'], ['Windows install'])

    def test_a_replaced_screen_is_caught(self):
        after = laptop()
        after['display'] = [{'manufacturer': 'BOE', 'product_code': '0A1C', 'year': 2024, 'serial_hash': None}]
        self.assertEqual(compare(laptop(), after)['changed'], ['Screen'])


class HonestyTests(SimpleTestCase):
    def test_a_part_that_could_not_be_read_is_not_called_unchanged(self):
        after = laptop()
        after['ram'] = None
        result = compare(laptop(), after)
        self.assertEqual(statuses(result)['Memory (RAM)'], 'not_checked')
        self.assertEqual(result['changed'], [])
        self.assertEqual(result['not_checked'], ['Memory (RAM)'])

    def test_a_serial_readable_in_only_one_scan_is_not_a_false_alarm(self):
        after = laptop()
        after['disks'][0]['serial_hash'] = None          # e.g. second scan was not run as administrator
        result = compare(laptop(), after)
        self.assertEqual(result['changed'], [])
        drive = next(c for c in result['components'] if c['component'] == 'Storage drive')
        self.assertTrue(any('Serial number could not be read' in i['detail'] for i in drive['items']))

    def test_two_identical_sticks_without_serials_still_match(self):
        before = laptop()
        for stick in before['ram']:
            stick['serial_hash'] = None
            stick['slot'] = 'DIMM A'
        after = copy.deepcopy(before)
        self.assertEqual(compare(before, after)['changed'], [])

    def test_the_limits_are_always_stated(self):
        self.assertIn('keyboard', compare(laptop(), laptop())['limits'])

    def test_snapshots_from_before_a_part_existed_do_not_crash(self):
        result = compare({}, {})
        self.assertEqual(len(result['not_checked']), 5)