import platform

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .comparison import compare
from .identifiers import collect_snapshot_from_windows, snapshot_summary
from .models import BlackoutEvent, SensorReading, HealthReading, NotificationSetting, Snapshot
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
            'battery_cycles': reading.battery_cycles,
            'drive_health': reading.drive_health,
        },
                'drives': [
            {
                'name': d.name,
                'media_type': d.media_type,
                'health_status': d.health_status,
                'temperature': d.temperature,
                'power_on_hours': d.power_on_hours,
                'wear': d.wear,
                'read_errors_uncorrected': d.read_errors_uncorrected,
            }
            for d in reading.disks.all().order_by('device_id')
        ],
        'trends': trends,
        **report,
    })

@api_view(['GET', 'POST'])
def notification_settings(request):
    """GET: what the owner chose.
    POST {"enabled": true/false} and/or {"email_enabled": true/false}: save the choice."""
    setting = NotificationSetting.current()
    if request.method == 'POST':
        fields = {k: request.data[k] for k in ('enabled', 'email_enabled') if k in request.data}
        if not fields or not all(isinstance(v, bool) for v in fields.values()):
            return Response({'detail': '"enabled" must be true or false'}, status=400)
        if 'enabled' in fields:
            setting.enabled = fields['enabled']
        if 'email_enabled' in fields:
            setting.email_enabled = fields['email_enabled']
        setting.asked = True
        setting.save()
    return Response({'enabled': setting.enabled, 'asked': setting.asked,
                     'email_enabled': setting.email_enabled})

@api_view(['GET', 'POST'])
def snapshots(request):
    """GET: the saved snapshots, newest first.
    POST {"label": "before"}: scan this laptop now and save the result.
    The scan only ever runs fixed commands. The label is just text we store."""
    if request.method == 'POST':
        label = request.data.get('label', 'scan')
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 60:
            return Response({'detail': '"label" must be short text, for example "before"'}, status=400)
        if platform.system() != 'Windows':
            return Response({'detail': 'Snapshots can only be taken on the Windows laptop.'}, status=501)
        data = collect_snapshot_from_windows()
        snapshot = Snapshot.objects.create(label=label.strip(), data=data)
        return Response(snapshot_summary(snapshot), status=201)
    return Response([snapshot_summary(s) for s in Snapshot.objects.all()[:20]])


@api_view(['GET'])
def snapshot_compare(request):
    """GET ?before=<id>&after=<id>: what changed between two saved snapshots."""
    try:
        before_id = int(request.query_params.get('before'))
        after_id = int(request.query_params.get('after'))
    except (TypeError, ValueError):
        return Response({'detail': 'Give two snapshot numbers: ?before=1&after=2'}, status=400)
    if before_id == after_id:
        return Response({'detail': 'Pick two different scans to compare.'}, status=400)
    before = Snapshot.objects.filter(pk=before_id).first()
    after = Snapshot.objects.filter(pk=after_id).first()
    if before is None or after is None:
        return Response({'detail': 'One of those snapshots does not exist.'}, status=404)
    result = compare(before.data, after.data)
    result['before'] = snapshot_summary(before)
    result['after'] = snapshot_summary(after)
    return Response(result)

@api_view(['GET'])
def blackouts(request):
    """The latest unexpected shutdowns found by check_blackout, newest first."""
    return Response([
        {'id': b.id, 'event_time': b.event_time, 'cause': b.cause,
         'bugcheck': b.bugcheck, 'summary': b.summary}
        for b in BlackoutEvent.objects.all()[:5]
    ])