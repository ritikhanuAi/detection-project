import pytest
from apps.jobs.models import Job
from apps.validation.models import DetectionRecord
from apps.validation.selectors import list_detections_for_job, get_validation_summary_for_job

@pytest.mark.django_db
def test_stage2_selectors_and_filtering():
    job = Job.objects.create(stage=Job.STAGE_STAGE2)
    
    # Create test records
    DetectionRecord.objects.create(
        job=job,
        detection_id="det_1",
        image_name="test1.jpg",
        class_name="pothole",
        ai_status=DetectionRecord.STATUS_CORRECT,
        ai_confidence=0.95,
        reason="Genuine pothole"
    )
    DetectionRecord.objects.create(
        job=job,
        detection_id="det_2",
        image_name="test2.jpg",
        class_name="crack",
        ai_status=DetectionRecord.STATUS_INCORRECT,
        ai_confidence=0.88,
        reason="Shadow look-alike"
    )
    DetectionRecord.objects.create(
        job=job,
        detection_id="det_3",
        image_name="test3.jpg",
        class_name="patch",
        ai_status=DetectionRecord.STATUS_NEEDS_REVIEW,
        ai_confidence=0.5,
        reason="Ambiguous edge"
    )

    # Test all detections
    all_dets = list_detections_for_job(job.id)
    assert all_dets.count() == 3

    # Test alias filtering: 'incorrect' and 'false'
    incorrect_dets = list_detections_for_job(job.id, status_filter="Incorrect")
    assert incorrect_dets.count() == 1
    assert incorrect_dets.first().detection_id == "det_2"

    false_dets = list_detections_for_job(job.id, status_filter="false")
    assert false_dets.count() == 1

    # Test 'correct' filter
    correct_dets = list_detections_for_job(job.id, status_filter="correct")
    assert correct_dets.count() == 1

    # Test 'review' filter
    review_dets = list_detections_for_job(job.id, status_filter="review")
    assert review_dets.count() == 1

    # Test summary aggregation
    summary = get_validation_summary_for_job(job.id)
    assert summary['total'] == 3
    assert summary['correct'] == 1
    assert summary['incorrect'] == 1
    assert summary['needs_review'] == 1
    assert summary['precision_rate'] == 33.3
