
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Investigation, LogEvent
from .serializers import (
    InvestigationDetailSerializer,
    InvestigationSerializer,
    LogEventSerializer,
)
from .services import (
    MAX_FILE_COUNT,
    export_events_to_csv,
    parse_log_content,
    validate_uploaded_file,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_view(request):
    return Response({
        'status': 'ok',
        'message': 'Django API is running.'
    })


class InvestigationListView(APIView):

    def get(self, request):
        investigations = Investigation.objects.all()
        serializer = InvestigationSerializer(
            investigations,
            many=True
        )
        return Response(serializer.data)

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        description = (request.data.get('description') or '').strip()

        if not name:
            return Response(
                {'detail': 'Investigation name is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        investigation = Investigation.objects.create(
            name=name,
            description=description,
            status='draft'
        )

        serializer = InvestigationSerializer(investigation)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


class InvestigationDetailView(APIView):

    def get(self, request, pk):
        investigation = get_object_or_404(
            Investigation,
            pk=pk
        )

        serializer = InvestigationDetailSerializer(
            investigation
        )

        return Response(serializer.data)

    def delete(self, request, pk):
        investigation = get_object_or_404(
            Investigation,
            pk=pk
        )

        investigation.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class InvestigationUploadView(APIView):

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):

        investigation = get_object_or_404(
            Investigation,
            pk=pk
        )

        uploaded_files = request.FILES.getlist('files')

        if not uploaded_files:
            return Response(
                {'detail': 'Please attach at least one JSON file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(uploaded_files) > MAX_FILE_COUNT:
            return Response(
                {
                    'detail':
                    f'You can upload at most {MAX_FILE_COUNT} files at a time.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed_files = []
        total_lines = 0
        skipped_lines = 0
        severity_counts = {}

        # Validate and parse all files first
        try:
            for uploaded_file in uploaded_files:

                validate_uploaded_file(uploaded_file)

                content = uploaded_file.read()

                try:
                    text = content.decode('utf-8-sig')

                except UnicodeDecodeError as exc:
                    raise ValidationError(
                        f'{uploaded_file.name}: '
                        'File must contain valid UTF-8 JSON.'
                    ) from exc

                parsed = parse_log_content(
                    text,
                    uploaded_file.name
                )

                parsed_files.append(parsed)

                total_lines += parsed['total_lines']
                skipped_lines += parsed['skipped_lines']

                for key, value in parsed['severity_counts'].items():
                    severity_counts[key] = (
                        severity_counts.get(key, 0) + value
                    )

        except ValidationError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save events atomically
        all_events = []

        with transaction.atomic():

            investigation.status = 'processing'

            investigation.save(
                update_fields=['status', 'updated_at']
            )

            for parsed in parsed_files:

                for event_data in parsed['events']:

                    event = LogEvent.objects.create(
                        investigation=investigation,
                        timestamp=event_data['timestamp'],
                        severity=event_data['severity'],
                        service_name=event_data['service_name'],
                        message=event_data['message'],
                        request_id=event_data['request_id'],
                        source_file=event_data['source_file'],
                        raw_log=event_data['raw_log'],
                    )

                    all_events.append(event)

            investigation.status = 'completed'

            investigation.uploaded_files = ', '.join(
                file.name for file in uploaded_files
            )

            investigation.save(
                update_fields=[
                    'status',
                    'uploaded_files',
                    'updated_at'
                ]
            )

        result = {
            'detail': 'Upload processed successfully.',
            'investigation': InvestigationSerializer(
                investigation
            ).data,
            'stats': {
                'total_lines': total_lines,
                'parsed_events': len(all_events),
                'skipped_lines': skipped_lines,
                'severity_counts': severity_counts,
            },
        }

        return Response(
            result,
            status=status.HTTP_201_CREATED
        )


class InvestigationEventsView(APIView):

    def get(self, request, pk):

        investigation = get_object_or_404(
            Investigation,
            pk=pk
        )

        queryset = investigation.events.all()

        severity = (
            request.query_params.get('severity') or ''
        ).strip().upper()

        service = (
            request.query_params.get('service') or ''
        ).strip()

        request_id = (
            request.query_params.get('request_id') or ''
        ).strip()

        search = (
            request.query_params.get('search') or ''
        ).strip()

        start = request.query_params.get('start')
        end = request.query_params.get('end')

        if severity and severity in {
            'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
        }:
            queryset = queryset.filter(severity=severity)

        if service:
            queryset = queryset.filter(
                service_name__icontains=service
            )

        if request_id:
            queryset = queryset.filter(
                request_id__icontains=request_id
            )

        if search:
            queryset = queryset.filter(
                Q(message__icontains=search)
                | Q(service_name__icontains=search)
                | Q(request_id__icontains=search)
            )

        if start:
            queryset = queryset.filter(timestamp__gte=start)

        if end:
            queryset = queryset.filter(timestamp__lte=end)

        queryset = queryset.order_by('timestamp', 'id')

        try:
            page_size = int(
                request.query_params.get('page_size', 20)
            )
            page = int(
                request.query_params.get('page', 1)
            )

        except ValueError:
            return Response(
                {'detail': 'Invalid pagination parameters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if page < 1:
            return Response(
                {'detail': 'Page must be greater than zero.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        page_size = min(max(page_size, 1), 100)

        offset = (page - 1) * page_size
        total = queryset.count()

        items = queryset[offset:offset + page_size]

        serializer = LogEventSerializer(
            items,
            many=True
        )

        response = {
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,
        }

        if offset + page_size < total:
            response['next'] = page + 1

        if offset > 0:
            response['previous'] = page - 1

        return Response(response)


class InvestigationCorrelationsView(APIView):

    def get(self, request, pk):

        investigation = get_object_or_404(
            Investigation,
            pk=pk
        )

        events = investigation.events.exclude(
            request_id=''
        ).order_by('timestamp')

        grouped = {}

        for event in events:
            grouped.setdefault(
                event.request_id,
                []
            ).append(event)

        correlations = []

        for request_id, items in grouped.items():

            if len(items) < 2:
                continue

            correlations.append({
                'request_id': request_id,
                'event_count': len(items),
                'services': sorted({
                    item.service_name
                    for item in items
                    if item.service_name
                }),
                'events': LogEventSerializer(
                    items,
                    many=True
                ).data,
            })

        return Response({
            'count': len(correlations),
            'results': correlations
        })


def export_investigation(request, pk):

    investigation = get_object_or_404(
        Investigation,
        pk=pk
    )

    events = investigation.events.all().order_by(
        'timestamp'
    )

    export_format = (
        request.GET.get('format') or 'json'
    ).lower()

    filename = (
        investigation.name.lower().replace(' ', '-')
    )

    if export_format == 'json':

        payload = {
            'investigation': {
                'id': str(investigation.id),
                'name': investigation.name,
                'description': investigation.description,
                'status': investigation.status,
            },
            'events': LogEventSerializer(
                events,
                many=True
            ).data,
        }

        response = HttpResponse(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2
            ),
            content_type='application/json'
        )

        response['Content-Disposition'] = (
            f'attachment; filename="{filename}-export.json"'
        )

        return response

    if export_format == 'csv':

        csv_data = export_events_to_csv(events)

        response = HttpResponse(
            csv_data,
            content_type='text/csv; charset=utf-8'
        )

        response['Content-Disposition'] = (
            f'attachment; filename="{filename}-export.csv"'
        )

        return response

    return JsonResponse(
        {
            'detail': 'Unsupported export format. Use json or csv.'
        },
        status=status.HTTP_400_BAD_REQUEST
    )
