from django.contrib import admin

from .models import Investigation, LogEvent


@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    search_fields = ('name', 'description')


@admin.register(LogEvent)
class LogEventAdmin(admin.ModelAdmin):
    list_display = ('investigation', 'timestamp', 'severity', 'service_name', 'request_id')
    list_filter = ('severity', 'service_name')
    search_fields = ('message', 'request_id', 'service_name')
