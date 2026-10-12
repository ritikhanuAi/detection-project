from django.urls import path
from .views import (
    JobListCreateAPIView,
    JobDetailAPIView,
    UploadSessionCreateAPIView,
    UploadSessionProgressAPIView,
)

app_name = 'jobs'

urlpatterns = [
    path('', JobListCreateAPIView.as_view(), name='job-list-create'),
    path('<uuid:job_id>/', JobDetailAPIView.as_view(), name='job-detail'),
    path('uploads/init/', UploadSessionCreateAPIView.as_view(), name='upload-init'),
    path('uploads/<uuid:session_id>/', UploadSessionProgressAPIView.as_view(), name='upload-progress'),
]
