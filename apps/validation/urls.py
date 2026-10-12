from django.urls import path
from .views import (
    DetectionListAPIView,
    DetectionSummaryAPIView,
    TriggerDetectionValidationAPIView,
    ExportValidatedJSONAPIView,
)

app_name = 'validation'

urlpatterns = [
    path('run/', TriggerDetectionValidationAPIView.as_view(), name='validation-run'),
    path('<uuid:job_id>/detections/', DetectionListAPIView.as_view(), name='detection-list'),
    path('<uuid:job_id>/summary/', DetectionSummaryAPIView.as_view(), name='detection-summary'),
    path('<uuid:job_id>/export/', ExportValidatedJSONAPIView.as_view(), name='detection-export'),
]
