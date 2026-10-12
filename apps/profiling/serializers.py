from rest_framework import serializers
from .models import RoadProfile, Keyframe


class KeyframeSerializer(serializers.ModelSerializer):
    """Serialization for individual keyframes."""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Keyframe
        fields = [
            'id',
            'index',
            'frame_number',
            'timestamp_s',
            'sharpness',
            'image',
            'image_url',
            'analysis',
            'analysed',
            'created_at',
        ]
        read_only_fields = fields

    def get_image_url(self, obj) -> str:
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ''


class RoadProfileSerializer(serializers.ModelSerializer):
    """Serialization for Stage 1 Road Profile results with telemetry."""
    keyframes = KeyframeSerializer(many=True, read_only=True)

    class Meta:
        model = RoadProfile
        fields = [
            'id',
            'job_id',
            'road_type',
            'pavement_type',
            'carriageway_type',
            'lanes',
            'estimated_width_m',
            'confidence_scores',
            'model_config_selected',
            'extracted_frames',
            'frame_details',
            'confidences',
            'votes',
            'overall_confidence',
            'frames_sampled',
            'frames_analysed',
            'frames_rejected_blur',
            'processing_seconds',
            'ai_provider',
            'keyframes',
            'created_at',
        ]
        read_only_fields = fields
