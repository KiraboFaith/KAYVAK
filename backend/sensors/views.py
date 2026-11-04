from rest_framework.decorators import api_view
from rest_framework.response import Response
from .dataset import load_summary, percentile_rank
from .models import DiskReading, SensorReading, HealthReading, NotificationSetting
from .analysis import (
    analyse, trend,
    BATTERY_WARNING, BATTERY_CRITICAL, DRIVE_WARNING, DRIVE_CRITICAL,
)

TREND_WINDOW = 20  # how many recent readings the trend looks at


@api_view(['GET'])
def sensor_data(request):
    reading = SensorReading.objects.latest('timestamp')

    data = {
        'temperature': reading.temperature,
        'humidity': reading.humidity,
        'status': reading.status,
        'log': [reading.log_entry],
    }
    return Response(data)


@api_view(['GET'])
def health_report(request):
    reading = HealthReading.objects.first()  # newest first
    if reading is None:
        return Response({'detail': 'No readings yet'}, status=404)

    report = analyse(reading)

    # Knowledge: look back at recent readings (oldest first) to see where things are heading
    recent = list(HealthReading.objects.all()[:TREND_WINDOW])[::-1]
    trends = {
        'battery': trend([r.battery_health for r in recent], BATTERY_WARNING, BATTERY_CRITICAL),
        'drive': trend(
            [r.drive_health for r in recent if r.drive_health is not None],
            DRIVE_WARNING, DRIVE_CRITICAL,
        ),
    }

    # Checks Windows would not answer: shown to the user, never silently counted as passed
    unchecked = []
    if not reading.licence_checked:
        unchecked.append('Windows licence')
    if not reading.malware_checked:
        unchecked.append('Security')
    if reading.drive_health is None:
        unchecked.append('Storage drive')

    return Response({
        'timestamp': reading.timestamp,
        'source': reading.source,
        'unchecked': unchecked,
        'check_seconds': reading.check_seconds,
        'measurements': {
            'battery_health': reading.battery_health,
            'drive_health': reading.drive_health,
        },
        'trends': trends,
        **report,
    })


@api_view(['GET', 'POST'])
def notification_settings(request):
    """GET: what the owner chose. POST {"enabled": true/false}: save the choice."""
    setting = NotificationSetting.current()
    if request.method == 'POST':
        enabled = request.data.get('enabled')
        if not isinstance(enabled, bool):
            return Response({'detail': '"enabled" must be true or false'}, status=400)
        setting.enabled = enabled
        setting.asked = True
        setting.save()
    return Response({'enabled': setting.enabled, 'asked': setting.asked})


DATASET_METRICS = [   # (field on DiskReading, name in the summary file, label shown to the user)
    ('power_on_hours', 'power_on_hours', 'Power-on hours'),
    ('load_unload_cycles', 'load_unload_cycles', 'Load/unload cycles'),
    ('temperature', 'temperature', 'Temperature (°C)'),
]


@api_view(['GET'])
def dataset_comparison(request):
    """Compares this laptop's latest disk numbers with real drives from the Backblaze dataset."""
    summary = load_summary()
    if summary is None:
        return Response({'detail': 'No dataset summary yet. Run analysis/export_summary.py'}, status=404)

    newest = DiskReading.objects.select_related('reading').first()  # newest first
    disks = list(newest.reading.disks.order_by('device_id')) if newest else []

    drives = []
    for disk in disks:
        item = {
            'device_id': disk.device_id,
            'name': disk.name,
            'media_type': disk.media_type,
            'checked_at': disk.timestamp,
            'metrics': [],
        }
        if disk.media_type != 'HDD':
            item['note'] = 'Not compared: the dataset only contains hard drives (HDD).'
        else:
            for field, key, label in DATASET_METRICS:
                value = getattr(disk, field)
                numbers = summary['metrics'].get(key)
                if value is None or numbers is None:
                    continue
                healthy, failed = numbers['healthy'], numbers['failed']
                middle = summary['points'].index(50)
                item['metrics'].append({
                    'key': key,
                    'label': label,
                    'value': value,
                    'percentile': round(percentile_rank(value, summary['points'], healthy), 1),
                    'outside_range': value < healthy[0] or value > healthy[-1],
                    'healthy_median': healthy[middle],
                    'failed_median': failed[middle] if failed else None,
                })
        drives.append(item)

    return Response({
        'dataset': {
            'source': summary['source'],
            'models': summary['models'],
            'date_from': summary['date_from'],
            'date_to': summary['date_to'],
            'healthy_drives': summary['healthy_drives'],
            'failed_drives': summary['failed_drives'],
        },
        'drives': drives,
        'caution': (
            'This compares your drive\'s numbers with real drives. It does not predict '
            'whether your drive will fail.'
        ),
    })