import uuid

from django.db import models


class Investigation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    uploaded_files = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class LogEvent(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(db_index=True)
    severity = models.CharField(max_length=16, default='INFO', db_index=True)
    service_name = models.CharField(max_length=200, blank=True, default='', db_index=True)
    message = models.TextField()
    request_id = models.CharField(max_length=250, blank=True, default='', db_index=True)
    source_file = models.CharField(max_length=255, blank=True, default='')
    raw_log = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['timestamp', 'id']
        indexes = [
            models.Index(fields=['investigation', 'timestamp']),
            models.Index(fields=['investigation', 'severity']),
            models.Index(fields=['investigation', 'service_name']),
            models.Index(fields=['investigation', 'request_id']),
        ]

    def __str__(self):
        return f'{self.severity} | {self.service_name} | {self.message[:80]}'
