from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def sensor_data(request):
    data = {
        'temperature': 24,
        'humidity': 58,
        'status': 'Normal',
        'log': [
            'Monitored: Temp 24°C, Humidity 58% — within normal range',
            'Analyzed: No anomaly detected',
            'Planned: No action needed',
            'Executed: System idle',
        ],
    }
    return Response(data)