import logging
from celery import shared_task
from .services import run_validation_pipeline

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=1)
def process_detection_validation_task(self, job_id: str, detections_data: list, image_search_dirs: list):
    """Celery task to run Stage 2 detection verification asynchronously."""
    logger.info(f"Starting Celery task for Detection Validation Job {job_id}")
    try:
        run_validation_pipeline(job_id, detections_data, image_search_dirs)
        logger.info(f"Successfully completed Detection Validation Job {job_id}")
    except Exception as exc:
        logger.exception(f"Error in Stage 2 Celery task for Job {job_id}: {exc}")
        raise exc
