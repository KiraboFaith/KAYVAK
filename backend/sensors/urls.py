from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.sensor_data, name='sensor-data'),
    path('health/', views.health_report, name='health-report'),
    path('dataset/', views.dataset_comparison, name='dataset-comparison'),
    path('notifications/', views.notification_settings, name='notification-settings'),
]
