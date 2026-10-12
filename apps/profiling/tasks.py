import logging
from celery import shared_task
from .services import run_road_profiling_pipeline

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=1)
def process_road_profiling_task(self, job_id: str):
    """Celery task to run Stage 1 profiling asynchronously in worker."""
    logger.info(f"Starting Celery task for Road Profiling Job {job_id}")
    try:
        run_road_profiling_pipeline(job_id)
        logger.info(f"Successfully completed Road Profiling Job {job_id}")
    except Exception as exc:
        logger.exception(f"Error in Celery task for Job {job_id}: {exc}")
        raise exc
