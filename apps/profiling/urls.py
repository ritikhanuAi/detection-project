from django.urls import path
from .views import RoadProfileDetailAPIView, TriggerRoadProfilingAPIView

app_name = 'profiling'

urlpatterns = [
    path('<uuid:job_id>/', RoadProfileDetailAPIView.as_view(), name='profile-detail'),
    path('<uuid:job_id>/trigger/', TriggerRoadProfilingAPIView.as_view(), name='profile-trigger'),
]
