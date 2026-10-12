from rest_framework import serializers
from .models import DetectionRecord

class DetectionRecordSerializer(serializers.ModelSerializer):
    """Output serialization for DetectionRecord."""
    crop_url = serializers.SerializerMethodField()
    annotated_url = serializers.SerializerMethodField()

    class Meta:
        model = DetectionRecord
        fields = [
            'id',
            'detection_id',
            'image_name',
            'class_name',
            'original_confidence',
            'bbox',
            'ai_status',
            'ai_confidence',
            'reason',
            'crop_url',
            'annotated_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_crop_url(self, obj):
        if obj.crop_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f"/media/{obj.crop_image}")
            return f"/media/{obj.crop_image}"
        return None

    def get_annotated_url(self, obj):
        if obj.annotated_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f"/media/{obj.annotated_image}")
            return f"/media/{obj.annotated_image}"
        return None


class SingleDetectionInputSerializer(serializers.Serializer):
    """Validation for a single detection record inside uploaded JSON."""
    id = serializers.CharField(required=False, default='')
    image_name = serializers.CharField(required=False, allow_blank=True, default='')
    image = serializers.CharField(required=False, allow_blank=True, default='')
    class_name = serializers.CharField(required=False, allow_blank=True, default='')
    label = serializers.CharField(required=False, allow_blank=True, default='')
    category = serializers.CharField(required=False, allow_blank=True, default='')
    confidence = serializers.FloatField(required=False, default=1.0)
    score = serializers.FloatField(required=False, default=1.0)
    bbox = serializers.JSONField(required=True)

    def validate(self, attrs):
        # Normalize class name
        c_name = attrs.get('class_name') or attrs.get('label') or attrs.get('category')
        if not c_name:
            c_name = 'defect'
        attrs['class_name'] = str(c_name).strip()

        # Normalize image name
        img_name = attrs.get('image_name') or attrs.get('image') or ''
        attrs['image_name'] = str(img_name).strip()

        # Normalize confidence
        attrs['confidence'] = attrs.get('confidence') or attrs.get('score', 1.0)
        return attrs
