from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient as _APIClient

from .models import Snapshot
from .test_comparison import laptop


def client():
    return _APIClient(HTTP_X_KAYVAK_CLIENT='dashboard')


class SnapshotApiTests(TestCase):
    url = '/api/sensors/snapshots/'

    def test_taking_a_snapshot_saves_it(self):
        with mock.patch('sensors.views.platform.system', return_value='Windows'), \
             mock.patch('sensors.views.collect_snapshot_from_windows', return_value=dict(laptop(), errors={})):
            response = client().post(self.url, {'label': 'before'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Snapshot.objects.get().label, 'before')
        self.assertEqual(response.data['unchecked'], [])

    def test_not_windows_is_refused_politely(self):
        with mock.patch('sensors.views.platform.system', return_value='Linux'):
            self.assertEqual(client().post(self.url, {'label': 'before'}, format='json').status_code, 501)

    def test_bad_label_is_rejected(self):
        for label in ('', '   ', 'x' * 61, 5):
            self.assertEqual(client().post(self.url, {'label': label}, format='json').status_code, 400, label)

    def test_list_shows_newest_first_without_serial_fingerprints(self):
        Snapshot.objects.create(label='before', data=dict(laptop(), errors={}))
        Snapshot.objects.create(label='after', data=dict(laptop(), ram=None, errors={'ram': 'denied'}))
        data = client().get(self.url).data
        self.assertEqual([s['label'] for s in data], ['after', 'before'])
        self.assertEqual(data[0]['unchecked'], ['ram'])
        self.assertNotIn('serial_hash', str(data))

    def test_requests_without_the_header_are_refused(self):
        self.assertEqual(_APIClient().get(self.url).status_code, 403)


class SnapshotCompareApiTests(TestCase):
    url = '/api/sensors/snapshots/compare/'

    def make(self, label, data=None):
        return Snapshot.objects.create(label=label, data=data or dict(laptop(), errors={}))

    def test_swapped_ram_is_reported_through_the_api(self):
        after_data = dict(laptop(), errors={})
        after_data['ram'][1] = dict(after_data['ram'][1], serial_hash='new', part_number='KVR')
        before, after = self.make('before'), self.make('after', after_data)
        data = client().get(self.url, {'before': before.id, 'after': after.id}).data
        self.assertEqual(data['changed'], ['Memory (RAM)'])
        self.assertEqual(data['before']['label'], 'before')
        self.assertIn('limits', data)
        self.assertNotIn('serial_hash', str(data))

    def test_missing_or_bad_numbers(self):
        self.assertEqual(client().get(self.url).status_code, 400)
        self.assertEqual(client().get(self.url, {'before': 'a', 'after': 'b'}).status_code, 400)

    def test_same_snapshot_twice_is_refused(self):
        one = self.make('before')
        self.assertEqual(client().get(self.url, {'before': one.id, 'after': one.id}).status_code, 400)

    def test_unknown_snapshot_is_404(self):
        one = self.make('before')
        self.assertEqual(client().get(self.url, {'before': one.id, 'after': 9999}).status_code, 404)