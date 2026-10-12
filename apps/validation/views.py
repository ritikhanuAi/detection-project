import os
import json
import zipfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, Http404
from django.conf import settings

from apps.core.pagination import StandardResultsPagination
from apps.jobs.models import Job
from apps.jobs.selectors import get_job_by_id
from apps.jobs.services import create_job_service
from .selectors import list_detections_for_job, get_validation_summary_for_job
from .serializers import DetectionRecordSerializer
from .tasks import process_detection_validation_task
from .services import run_validation_pipeline

class DetectionListAPIView(APIView):
    """List verified detections for a job with filtering, search, and pagination."""
    pagination_class = StandardResultsPagination

    def get(self, request, job_id):
        status_filter = request.query_params.get('status')
        class_search = request.query_params.get('search')
        ordering = request.query_params.get('ordering', 'id')

        qs = list_detections_for_job(
            job_id=job_id,
            status_filter=status_filter,
            class_search=class_search,
            ordering=ordering
        )

        paginator = self.pagination_class()
        paginated_records = paginator.paginate_queryset(qs, request)
        serializer = DetectionRecordSerializer(paginated_records, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class DetectionSummaryAPIView(APIView):
    """Returns verdict metrics (correct, incorrect, needs review counts, precision rate)."""

    def get(self, request, job_id):
        summary = get_validation_summary_for_job(job_id)
        return Response(summary)


class TriggerDetectionValidationAPIView(APIView):
    """
    Accepts:
    1. json_file: Detections JSON file (list of bounding boxes and class names).
    2. images_zip (optional): Zip archive containing source road frames.
    Creates a Stage 2 job and kicks off validation asynchronously.
    """

    def post(self, request):
        json_file = request.FILES.get('json_file')
        images_zip = request.FILES.get('images_zip')

        if not json_file:
            return Response({'error': 'json_file is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            detections_content = json.load(json_file)
            if isinstance(detections_content, dict):
                # Check if wrapped in results or detections key
                detections_list = detections_content.get('detections', detections_content.get('results', []))
            elif isinstance(detections_content, list):
                detections_list = detections_content
            else:
                return Response({'error': 'Invalid JSON format: expected list or object with detections key'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to parse JSON file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Create Job
        job = create_job_service(
            stage=Job.STAGE_STAGE2,
            input_file=json_file,
            input_meta={'total_input_detections': len(detections_list)}
        )

        # Handle images archive if uploaded
        image_search_dirs = [settings.MEDIA_ROOT]
        if images_zip:
            extract_dir = os.path.join(settings.MEDIA_ROOT, 'uploads_extracted', str(job.id))
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(images_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            image_search_dirs.insert(0, extract_dir)

        # Dispatch Celery task with sync fallback
        try:
            process_detection_validation_task.delay(str(job.id), detections_list, image_search_dirs)
            mode = "async_celery"
        except Exception:
            run_validation_pipeline(str(job.id), detections_list, image_search_dirs)
            mode = "sync_fallback"

        return Response({
            'message': 'Detection validation pipeline started',
            'job_id': str(job.id),
            'total_detections': len(detections_list),
            'execution_mode': mode
        }, status=status.HTTP_202_ACCEPTED)


class ExportValidatedJSONAPIView(APIView):
    """Download validated JSON file containing verdicts and AI reasoning."""

    def get(self, request, job_id):
        export_path = os.path.join(settings.MEDIA_ROOT, 'exports', str(job_id), 'validated_detections.json')
        if not os.path.exists(export_path):
            raise Http404("Validated JSON export file not found.")

        return FileResponse(
            open(export_path, 'rb'),
            as_attachment=True,
            filename=f"roadathena_validated_{job_id}.json",
            content_type='application/json'
        )
