from rest_framework import serializers

from .models import Investigation, LogEvent


class LogEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEvent
        fields = [
            'id',
            'timestamp',
            'severity',
            'service_name',
            'message',
            'request_id',
            'source_file',
            'raw_log',
        ]


class InvestigationSerializer(serializers.ModelSerializer):
    event_count = serializers.SerializerMethodField()
    error_count = serializers.SerializerMethodField()
    critical_count = serializers.SerializerMethodField()

    class Meta:
        model = Investigation
        fields = [
            'id',
            'name',
            'description',
            'status',
            'uploaded_files',
            'created_at',
            'updated_at',
            'event_count',
            'error_count',
            'critical_count',
        ]

    def get_event_count(self, obj):
        return obj.events.count()

    def get_error_count(self, obj):
        return obj.events.filter(severity='ERROR').count()

    def get_critical_count(self, obj):
        return obj.events.filter(severity='CRITICAL').count()


class InvestigationDetailSerializer(InvestigationSerializer):
    pass
