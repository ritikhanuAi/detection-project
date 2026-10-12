from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Count
from .models import DetectionRecord

def list_detections_for_job(
    job_id: str,
    status_filter: Optional[str] = None,
    class_search: Optional[str] = None,
    ordering: str = 'id'
) -> QuerySet[DetectionRecord]:
    """Pure read selector returning filtered and ordered detections for a job."""
    qs = DetectionRecord.objects.filter(job_id=job_id)

    if status_filter:
        s_lower = status_filter.strip().lower()
        if s_lower in ['incorrect', 'false', 'incorrect/false']:
            qs = qs.filter(ai_status=DetectionRecord.STATUS_INCORRECT)
        elif s_lower in ['correct', 'true']:
            qs = qs.filter(ai_status=DetectionRecord.STATUS_CORRECT)
        elif s_lower in ['review', 'needs review', 'needs_review']:
            qs = qs.filter(ai_status=DetectionRecord.STATUS_NEEDS_REVIEW)
        else:
            qs = qs.filter(ai_status=status_filter)

    if class_search:
        qs = qs.filter(
            Q(class_name__icontains=class_search) |
            Q(image_name__icontains=class_search) |
            Q(reason__icontains=class_search)
        )

    allowed_orderings = [
        'id', '-id',
        'class_name', '-class_name',
        'original_confidence', '-original_confidence',
        'ai_status', '-ai_status',
        'created_at', '-created_at'
    ]
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('id')

    return qs

def get_detection_by_id(pk: int) -> Optional[DetectionRecord]:
    """Pure read selector to fetch single detection by primary key."""
    try:
        return DetectionRecord.objects.filter(id=pk).first()
    except Exception:
        return None

def get_validation_summary_for_job(job_id: str) -> Dict[str, Any]:
    """Aggregates verdict statistics (total, correct, false, needs review) for a job."""
    counts = (
        DetectionRecord.objects.filter(job_id=job_id)
        .values('ai_status')
        .annotate(total=Count('id'))
    )
    summary = {
        'total': 0,
        'correct': 0,
        'incorrect': 0,
        'needs_review': 0,
        'precision_rate': 0.0
    }
    for item in counts:
        status_val = item['ai_status']
        cnt = item['total']
        summary['total'] += cnt
        if status_val == DetectionRecord.STATUS_CORRECT:
            summary['correct'] += cnt
        elif status_val == DetectionRecord.STATUS_INCORRECT:
            summary['incorrect'] += cnt
        elif status_val == DetectionRecord.STATUS_NEEDS_REVIEW:
            summary['needs_review'] += cnt

    if summary['total'] > 0:
        summary['precision_rate'] = round((summary['correct'] / summary['total']) * 100, 1)

    return summary
