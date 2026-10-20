from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SensorReading, HealthReading, NotificationSetting
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
        'drive': trend([r.drive_health for r in recent], DRIVE_WARNING, DRIVE_CRITICAL),
    }

        # Checks Windows would not answer: shown to the user, never silently counted as passed
    unchecked = []
    if not reading.licence_checked:
        unchecked.append('Windows licence')
    if not reading.malware_checked:
        unchecked.append('Security')

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
