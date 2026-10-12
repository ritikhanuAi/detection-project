from django.db import models
from apps.jobs.models import Job

class DetectionRecord(models.Model):
    STATUS_CORRECT = 'Correct'
    STATUS_INCORRECT = 'Incorrect/False'
    STATUS_NEEDS_REVIEW = 'Needs Review'
    STATUS_CHOICES = [
        (STATUS_CORRECT, 'Correct'),
        (STATUS_INCORRECT, 'Incorrect/False'),
        (STATUS_NEEDS_REVIEW, 'Needs Review'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='detections')
    detection_id = models.CharField(max_length=120, db_index=True)
    image_name = models.CharField(max_length=255, db_index=True)
    class_name = models.CharField(max_length=120, db_index=True)
    original_confidence = models.FloatField(default=1.0)
    bbox = models.JSONField(default=dict)
    
    # AI Verdict & Rationale
    ai_status = models.CharField(max_length=30, choices=STATUS_CHOICES, db_index=True)
    ai_confidence = models.FloatField(default=0.0)
    reason = models.TextField(blank=True, default='')

    # Visual Artifacts
    crop_image = models.CharField(max_length=255, blank=True, default='')
    annotated_image = models.CharField(max_length=255, blank=True, default='')
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Detection {self.detection_id} ({self.class_name}) - {self.ai_status}"
