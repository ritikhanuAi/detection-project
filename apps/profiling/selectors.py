from typing import Optional
from .models import RoadProfile


def get_road_profile_for_job(job_id: str) -> Optional[RoadProfile]:
    """Pure read selector for fetching the RoadProfile associated with a job with prefetched keyframes."""
    try:
        return RoadProfile.objects.filter(job_id=job_id).prefetch_related('keyframes').first()
    except Exception:
        return None
