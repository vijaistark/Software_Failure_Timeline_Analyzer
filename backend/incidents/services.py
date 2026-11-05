
import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils import timezone

SEVERITY_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
SUPPORTED_EXTENSIONS = {'.json'}
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024
MAX_FILE_COUNT = 10


def normalize_severity(value):
    if not value:
        return 'INFO'

    cleaned = str(value).strip().upper()
    aliases = {'WARN': 'WARNING', 'ERR': 'ERROR', 'FATAL': 'CRITICAL'}

    if cleaned in aliases:
        return aliases[cleaned]

    if cleaned in SEVERITY_LEVELS:
        return cleaned

    return 'INFO'


def parse_timestamp(value):
    if value is None:
        return None

    if not str(value).strip():
        return None

    text = str(value).strip()
    text = text.replace('Z', '+00:00') if text.endswith('Z') else text

    iso_candidates = [
        '%Y-%m-%d %H:%M:%S,%f',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S,%f',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S,%f',
        '%Y/%m/%d %H:%M:%S.%f',
    ]

    for fmt in iso_candidates:
        try:
            parsed = datetime.strptime(text, fmt)

            if timezone.is_naive(parsed):
                return timezone.make_aware(
                    parsed,
                    timezone.get_current_timezone()
                )

            return parsed

        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(text)

        if timezone.is_naive(parsed):
            return timezone.make_aware(
                parsed,
                timezone.get_current_timezone()
            )

        return parsed

    except ValueError:
        return None


def extract_request_id(text):
    if not text:
        return ''

    patterns = [
        r'request[\_-]?id\s*[:=]\s*([A-Za-z0-9.\_-]+)',
        r'correlation[\_-]?id\s*[:=]\s*([A-Za-z0-9.\_-]+)',
        r'request[\_-]?id\s*[:=]\s*"([^"]+)"',
        r'\breq[-_]?\w+[A-Za-z0-9.\_-]*\b',
    ]

    lowered = text.lower()

    if (
        'request_id' not in lowered
        and 'correlation_id' not in lowered
        and 'requestid' not in lowered
    ):
        return ''

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            value = match.group(1).strip().strip('"\'') if match.lastindex else match.group(0)

            if value:
                return value

    return ''


def extract_service_name(text):
    if not text:
        return ''

    service_match = re.search(
        r'\[(?P<service>[^\]]+)\]',
        text
    )

    if service_match:
        return service_match.group('service').strip()

    service_key_match = re.search(
        r'(?:service|service_name|app|component)\s*[:=]\s*"?([A-Za-z0-9.\_-]+)"?',
        text,
        re.IGNORECASE
    )

    if service_key_match:
        return service_key_match.group(1).strip()

    return ''


def safest_message(value):
    if value is None:
        return ''

    return str(value).strip()


def parse_json_log_payload(payload, source_name):
    if isinstance(payload, dict):
        items = [payload]

    elif isinstance(payload, list):
        items = payload

    else:
        raise ValidationError(
            'JSON log content must be an object or list of objects.'
        )

    if not items:
        raise ValidationError(
            'JSON log file must contain at least one log record.'
        )

    if not all(isinstance(item, dict) for item in items):
        raise ValidationError(
            'JSON log file must contain only objects or a single object.'
        )

    events = []

    for item in items:
        timestamp = parse_timestamp(
            item.get('timestamp')
            or item.get('time')
            or item.get('created_at')
        )

        if timestamp is None:
            continue

        severity = normalize_severity(
            item.get('level')
            or item.get('severity')
            or item.get('log_level')
            or item.get('lvl')
        )

        service_name = safest_message(
            item.get('service')
            or item.get('service_name')
            or item.get('app')
            or item.get('component')
            or ''
        )

        message = safest_message(
            item.get('message')
            or item.get('msg')
            or item.get('log')
            or item.get('event')
        )

        request_id = safest_message(
            item.get('request_id')
            or item.get('requestId')
            or item.get('correlation_id')
            or item.get('trace_id')
            or ''
        )

        if not message and item.get('details'):
            message = safest_message(item.get('details'))

        events.append({
            'timestamp': timestamp,
            'severity': severity,
            'service_name': service_name,
            'message': message,
            'request_id': request_id,
            'source_file': source_name,
            'raw_log': json.dumps(item, ensure_ascii=False),
        })

    if not events:
        raise ValidationError(
            f'{source_name}: No valid log events found. '
            'Each log must contain a valid timestamp.'
        )

    return events


def parse_text_line(line):
    stripped = line.strip()

    if not stripped:
        return None

    match = re.match(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?)\s+(?P<level>[A-Z]+)\s*(?:\[(?P<service>[^\]]+)\]\s*)?(?P<message>.*)$',
        stripped
    )

    if not match:
        match = re.match(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?)\s+(?P<level>[A-Z]+)\s+(?P<message>.*)$',
            stripped
        )

        if not match:
            return None

    timestamp_text = match.group('timestamp')
    level = normalize_severity(match.group('level'))
    service_name = match.group('service') or ''
    message = match.group('message').strip()

    request_id = extract_request_id(message)

    if not service_name:
        service_name = extract_service_name(message)

    if not message:
        return None

    timestamp = parse_timestamp(timestamp_text)

    if timestamp is None:
        return None

    return {
        'timestamp': timestamp,
        'severity': level,
        'service_name': service_name,
        'message': message,
        'request_id': request_id,
        'source_file': '',
        'raw_log': stripped,
    }


def parse_log_content(content, source_name):
    if content is None or not str(content).strip():
        raise ValidationError(
            'Uploaded file is empty or contains no readable content.'
        )

    total_lines = 0
    skipped_lines = 0
    parsed_events = []
    severity_counts = defaultdict(int)

    lower_name = str(source_name).lower()

    if lower_name.endswith('.json'):
        try:
            payload = json.loads(content)

        except json.JSONDecodeError as exc:
            raise ValidationError(
                f'Invalid JSON content in {source_name}: {exc.msg}.'
            ) from exc

        parsed_events = parse_json_log_payload(
            payload,
            source_name
        )

        for event in parsed_events:
            severity_counts[event['severity']] += 1

        total_lines = max(1, len(parsed_events))
        skipped_lines = 0

        return {
            'total_lines': total_lines,
            'parsed_events': len(parsed_events),
            'skipped_lines': skipped_lines,
            'severity_counts': dict(severity_counts),
            'events': parsed_events,
        }

    for raw_line in str(content).splitlines():
        total_lines += 1

        if not raw_line.strip():
            skipped_lines += 1
            continue

        event = parse_text_line(raw_line)

        if event is None:
            skipped_lines += 1
            continue

        event['source_file'] = source_name

        severity_counts[event['severity']] += 1
        parsed_events.append(event)

    return {
        'total_lines': total_lines,
        'parsed_events': len(parsed_events),
        'skipped_lines': skipped_lines,
        'severity_counts': dict(severity_counts),
        'events': parsed_events,
    }


def validate_uploaded_file(file_obj):
    if file_obj is None:
        raise ValidationError('No file was provided.')

    suffix = Path(file_obj.name).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f'{file_obj.name}: Only JSON files are allowed.'
        )

    if file_obj.size == 0:
        raise ValidationError(
            f'{file_obj.name}: Empty files are not allowed.'
        )

    if file_obj.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f'{file_obj.name}: File size must not exceed 1 MB.'
        )

    return suffix


def export_events_to_csv(events):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'timestamp',
        'severity',
        'service',
        'message',
        'request_id',
        'source_file'
    ])

    for event in events:
        writer.writerow([
            event.timestamp.isoformat(),
            event.severity,
            event.service_name,
            event.message,
            event.request_id,
            event.source_file,
        ])

    return output.getvalue()
