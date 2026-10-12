import uuid
from django.db import models
from apps.jobs.models import Job


def keyframe_path(instance, filename):
    return f"frames/{instance.profile.job_id}/{filename}"


class RoadProfile(models.Model):
    ROAD_TYPE_CHOICES = [
        ('Highway', 'Highway'),
        ('Arterial', 'Arterial'),
        ('Collector', 'Collector'),
        ('Local Street', 'Local Street'),
        ('Rural Road', 'Rural Road'),
        ('Service Road', 'Service Road'),
        ('Urban', 'Urban'),
        ('Rural', 'Rural'),
        ('Unknown', 'Unknown'),
    ]
    PAVEMENT_TYPE_CHOICES = [
        ('Asphalt', 'Asphalt'),
        ('Concrete', 'Concrete'),
        ('Composite', 'Composite'),
        ('Gravel', 'Gravel'),
        ('Unpaved', 'Unpaved'),
        ('Unknown', 'Unknown'),
    ]
    CARRIAGEWAY_TYPE_CHOICES = [
        ('Divided', 'Divided'),
        ('Undivided', 'Undivided'),
        ('Single Carriageway', 'Single Carriageway'),
        ('Dual Carriageway', 'Dual Carriageway'),
        ('One-way', 'One-way'),
        ('Unknown', 'Unknown'),
    ]

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='road_profile')
    road_type = models.CharField(max_length=50, choices=ROAD_TYPE_CHOICES)
    pavement_type = models.CharField(max_length=50, choices=PAVEMENT_TYPE_CHOICES)
    carriageway_type = models.CharField(max_length=50, choices=CARRIAGEWAY_TYPE_CHOICES)
    lanes = models.IntegerField(default=2)
    estimated_width_m = models.FloatField(default=7.0)
    confidence_scores = models.JSONField(default=dict, blank=True)
    model_config_selected = models.CharField(max_length=150)
    extracted_frames = models.JSONField(default=list, blank=True)
    frame_details = models.JSONField(default=list, blank=True)

    # Telemetry and consensus fields
    confidences = models.JSONField(default=dict, blank=True)
    votes = models.JSONField(default=dict, blank=True)
    overall_confidence = models.FloatField(default=0.0)
    frames_sampled = models.IntegerField(default=0)
    frames_analysed = models.IntegerField(default=0)
    frames_rejected_blur = models.IntegerField(default=0)
    processing_seconds = models.FloatField(default=0.0)
    ai_provider = models.CharField(max_length=50, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RoadProfile for Job {self.job_id}: {self.road_type} / {self.pavement_type} ({self.model_config_selected})"


class Keyframe(models.Model):
    """Individual sharp keyframe extracted from video with analysis metadata."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(RoadProfile, on_delete=models.CASCADE, related_name="keyframes")
    index = models.PositiveSmallIntegerField(default=0)
    frame_number = models.PositiveIntegerField(default=0)
    timestamp_s = models.FloatField(default=0.0)
    sharpness = models.FloatField(default=0.0)
    image = models.ImageField(upload_to=keyframe_path, max_length=512)
    analysis = models.JSONField(default=dict, blank=True)
    analysed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['index']

    def __str__(self):
        return f"Keyframe {self.index} for Profile {self.profile_id} (sharpness={self.sharpness:.1f})"
