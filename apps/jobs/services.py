from typing import Optional, Dict, Any
from django.db import transaction
from django.core.files import File
from .models import Job, UploadSession

@transaction.atomic
def create_job_service(stage: str, input_file: Optional[File] = None, input_meta: Optional[Dict[str, Any]] = None) -> Job:
    """Business service to initialize and persist a new inspection Job."""
    job = Job(
        stage=stage,
        status=Job.STATUS_QUEUED,
        progress_percent=0,
        progress_message="Job queued for processing",
        input_meta=input_meta or {}
    )
    if input_file:
        job.input_file = input_file
    job.save()
    return job

@transaction.atomic
def update_job_progress_service(
    job: Job,
    progress_percent: int,
    progress_message: str,
    status: Optional[str] = None
) -> Job:
    """Updates job progress and status with validation."""
    job.progress_percent = max(0, min(100, progress_percent))
    job.progress_message = progress_message
    if status:
        job.status = status
    job.save(update_fields=['progress_percent', 'progress_message', 'status', 'updated_at'])
    return job

@transaction.atomic
def mark_job_failed_service(job: Job, error_message: str) -> Job:
    """Marks a job as failed and records the exception trace/summary."""
    job.status = Job.STATUS_FAILED
    job.error_message = error_message
    job.progress_message = f"Failed: {error_message[:100]}"
    job.save(update_fields=['status', 'error_message', 'progress_message', 'updated_at'])
    return job

@transaction.atomic
def init_upload_session_service(file_name: str, file_type: str = '', total_bytes: int = 0) -> UploadSession:
    """Initializes a new upload session to track file transfer percentage."""
    session = UploadSession.objects.create(
        file_name=file_name,
        file_type=file_type,
        total_bytes=total_bytes,
        uploaded_bytes=0,
        is_completed=False
    )
    return session

@transaction.atomic
def update_upload_session_service(session: UploadSession, uploaded_bytes: int, is_completed: bool = False) -> UploadSession:
    """Updates uploaded byte count and completion state."""
    session.uploaded_bytes = uploaded_bytes
    session.is_completed = is_completed
    session.save(update_fields=['uploaded_bytes', 'is_completed', 'updated_at'])
    return session
