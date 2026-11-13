from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.sensor_data, name='sensor-data'),
    path('health/', views.health_report, name='health-report'),
    path('notifications/', views.notification_settings, name='notification-settings'),
    path('blackouts/', views.blackouts, name='blackouts'),
    path('snapshots/', views.snapshots, name='snapshots'),
    path('snapshots/compare/', views.snapshot_compare, name='snapshot-compare'),
    path('snapshots/<int:pk>/', views.snapshot_detail, name='snapshot-detail'),
]