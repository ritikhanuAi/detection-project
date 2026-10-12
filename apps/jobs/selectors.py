from typing import Optional
from django.db.models import QuerySet, Q
from .models import Job, UploadSession

def get_job_by_id(job_id: str) -> Optional[Job]:
    """Pure read selector for fetching a Job by its UUID."""
    try:
        return Job.objects.filter(id=job_id).first()
    except Exception:
        return None

def list_jobs_selector(
    stage: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    ordering: str = '-created_at'
) -> QuerySet[Job]:
    """
    Pure read selector for listing and filtering Jobs.
    Applies stage, status, search keyword, and ordering safely.
    """
    qs = Job.objects.all()

    if stage:
        qs = qs.filter(stage=stage)

    if status:
        qs = qs.filter(status=status)

    if search:
        qs = qs.filter(
            Q(id__icontains=search) |
            Q(progress_message__icontains=search) |
            Q(error_message__icontains=search)
        )

    allowed_orderings = ['created_at', '-created_at', 'status', '-status', 'stage', '-stage']
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-created_at')

    return qs

def get_upload_session_by_id(session_id: str) -> Optional[UploadSession]:
    """Pure read selector for fetching an UploadSession by UUID."""
    try:
        return UploadSession.objects.filter(id=session_id).first()
    except Exception:
        return None
