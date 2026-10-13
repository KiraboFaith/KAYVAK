from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SensorReading, HealthReading
from .analysis import analyse


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
    return Response({
        'timestamp': reading.timestamp,
        'measurements': {
            'battery_health': reading.battery_health,
            'drive_health': reading.drive_health,
        },
        **report,
    })


