from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SensorReading


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


