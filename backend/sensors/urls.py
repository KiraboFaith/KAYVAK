from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.sensor_data, name='sensor-data'),
]
