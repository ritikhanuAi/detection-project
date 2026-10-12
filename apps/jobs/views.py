from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.pagination import StandardResultsPagination
from .serializers import JobCreateSerializer, JobDetailSerializer, UploadSessionSerializer
from .selectors import get_job_by_id, list_jobs_selector, get_upload_session_by_id
from .services import (
    create_job_service,
    init_upload_session_service,
    update_upload_session_service
)

class JobListCreateAPIView(APIView):
    """
    List jobs with pagination, filtering & sorting (Selector).
    Create new job after strict validation (Serializer -> Service).
    """
    pagination_class = StandardResultsPagination

    def get(self, request):
        stage = request.query_params.get('stage')
        job_status = request.query_params.get('status')
        search = request.query_params.get('search')
        ordering = request.query_params.get('ordering', '-created_at')

        jobs_qs = list_jobs_selector(stage=stage, status=job_status, search=search, ordering=ordering)
        
        paginator = self.pagination_class()
        paginated_jobs = paginator.paginate_queryset(jobs_qs, request)
        serializer = JobDetailSerializer(paginated_jobs, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        job = create_job_service(
            stage=validated_data['stage'],
            input_file=request.FILES.get('input_file'),
            input_meta=validated_data.get('input_meta', {})
        )
        return Response(JobDetailSerializer(job, context={'request': request}).data, status=status.HTTP_201_CREATED)


class JobDetailAPIView(APIView):
    """Fetch status and details of a single job."""

    def get(self, request, job_id):
        job = get_job_by_id(job_id)
        if not job:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = JobDetailSerializer(job, context={'request': request})
        return Response(serializer.data)


class UploadSessionCreateAPIView(APIView):
    """Initializes an upload session for progress tracking."""

    def post(self, request):
        file_name = request.data.get('file_name', 'upload.dat')
        file_type = request.data.get('file_type', '')
        total_bytes = int(request.data.get('total_bytes', 0))

        session = init_upload_session_service(file_name, file_type, total_bytes)
        return Response(UploadSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class UploadSessionProgressAPIView(APIView):
    """Updates and retrieves progress for an upload session."""

    def get(self, request, session_id):
        session = get_upload_session_by_id(session_id)
        if not session:
            return Response({'error': 'Upload session not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UploadSessionSerializer(session).data)

    def post(self, request, session_id):
        session = get_upload_session_by_id(session_id)
        if not session:
            return Response({'error': 'Upload session not found'}, status=status.HTTP_404_NOT_FOUND)
        
        uploaded_bytes = int(request.data.get('uploaded_bytes', session.uploaded_bytes))
        is_completed = bool(request.data.get('is_completed', False))
        
        updated_session = update_upload_session_service(session, uploaded_bytes, is_completed)
        return Response(UploadSessionSerializer(updated_session).data)
