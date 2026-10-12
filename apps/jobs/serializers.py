from rest_framework import serializers
from .models import Job, UploadSession

class JobCreateSerializer(serializers.Serializer):
    """Validation only for creating a new Job."""
    stage = serializers.ChoiceField(choices=Job.STAGE_CHOICES)
    input_file = serializers.FileField(required=False)
    input_meta = serializers.JSONField(required=False, default=dict)

    def validate_stage(self, value):
        if value not in [Job.STAGE_STAGE1, Job.STAGE_STAGE2]:
            raise serializers.ValidationError("Invalid job stage.")
        return value


class JobDetailSerializer(serializers.ModelSerializer):
    """Serialization for Job status & details."""
    input_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'stage',
            'status',
            'progress_percent',
            'progress_message',
            'input_file_url',
            'input_meta',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_input_file_url(self, obj):
        if obj.input_file and hasattr(obj.input_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.input_file.url)
            return obj.input_file.url
        return None


class UploadSessionSerializer(serializers.ModelSerializer):
    """Serialization for upload session progress tracking."""
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = UploadSession
        fields = [
            'id',
            'file_name',
            'file_type',
            'total_bytes',
            'uploaded_bytes',
            'percentage',
            'is_completed',
            'created_at',
        ]
        read_only_fields = fields
