from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.jobs.selectors import get_job_by_id
from apps.jobs.models import Job
from .selectors import get_road_profile_for_job
from .serializers import RoadProfileSerializer
from .tasks import process_road_profiling_task
from .services import run_road_profiling_pipeline

class RoadProfileDetailAPIView(APIView):
    """Retrieve the Stage 1 road profile results for a specific job."""

    def get(self, request, job_id):
        profile = get_road_profile_for_job(job_id)
        if not profile:
            return Response({'error': 'Road profile not found or still processing'}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoadProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)


class TriggerRoadProfilingAPIView(APIView):
    """Trigger the profiling pipeline asynchronously for an uploaded video job."""

    def post(self, request, job_id):
        job = get_job_by_id(job_id)
        if not job:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        if not job.input_file:
            return Response({'error': 'Job has no video file attached'}, status=status.HTTP_400_BAD_REQUEST)
        if job.status == Job.STATUS_RUNNING:
            return Response({'message': 'Job is already running'}, status=status.HTTP_200_OK)

        # Dispatch task to Celery with fallback to synchronous execution if redis is unavailable
        try:
            process_road_profiling_task.delay(str(job.id))
            mode = "async_celery"
        except Exception:
            run_road_profiling_pipeline(str(job.id))
            mode = "sync_fallback"

        return Response({
            'message': 'Road profiling pipeline started',
            'job_id': str(job.id),
            'execution_mode': mode
        }, status=status.HTTP_202_ACCEPTED)
