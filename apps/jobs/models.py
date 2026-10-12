import uuid
from django.db import models

class Job(models.Model):
    STAGE_STAGE1 = 'stage1'
    STAGE_STAGE2 = 'stage2'
    STAGE_CHOICES = [
        (STAGE_STAGE1, 'Stage 1: Road Profiling'),
        (STAGE_STAGE2, 'Stage 2: Detection Validator'),
    ]

    STATUS_QUEUED = 'queued'
    STATUS_UPLOADING = 'uploading'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_UPLOADING, 'Uploading'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    progress_percent = models.IntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True, default='')
    input_file = models.FileField(upload_to='inputs/%Y/%m/%d/', null=True, blank=True)
    input_meta = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Job {self.id} [{self.stage}] - {self.status}"


class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, blank=True, default='')
    total_bytes = models.BigIntegerField(default=0)
    uploaded_bytes = models.BigIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def percentage(self) -> int:
        if self.total_bytes <= 0:
            return 100 if self.is_completed else 0
        return min(100, int((self.uploaded_bytes / self.total_bytes) * 100))

    def __str__(self):
        return f"UploadSession {self.id} - {self.file_name} ({self.percentage}%)"
