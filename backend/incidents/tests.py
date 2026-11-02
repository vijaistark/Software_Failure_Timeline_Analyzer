import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from incidents.models import Investigation, LogEvent
from incidents.services import extract_request_id, normalize_severity, parse_log_content, parse_timestamp


class IncidentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_investigation_creation_and_retrieval(self):
        response = self.client.post('/api/investigations/', {'name': 'Checkout outage', 'description': 'Investigating payment errors.'}, format='json')
        self.assertEqual(response.status_code, 201)

        investigation_id = response.json()['id']
        fetch_response = self.client.get(f'/api/investigations/{investigation_id}/')
        self.assertEqual(fetch_response.status_code, 200)
        self.assertEqual(fetch_response.json()['name'], 'Checkout outage')

    def test_valid_log_upload(self):
        investigation = Investigation.objects.create(name='Website outage')
        log_content = (
            '2026-10-30 10:15:30 INFO [payment-service] Payment request received request_id=req-101\n'
            '2026-10-30 10:15:32 ERROR [payment-service] Database connection failed request_id=req-101\n'
            '2026-10-30 10:15:33 WARNING [auth-service] Retry triggered request_id=req-202\n'
        )

        response = self.client.post(
            f'/api/investigations/{investigation.id}/upload/',
            {'files': [self._make_file('sample.log', log_content.encode('utf-8'))]},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['stats']['parsed_events'], 3)
        self.assertTrue(LogEvent.objects.filter(investigation=investigation).exists())

    def test_invalid_file_handling(self):
        investigation = Investigation.objects.create(name='Invalid file case')
        response = self.client.post(
            f'/api/investigations/{investigation.id}/upload/',
            {'files': [self._make_file('notes.csv', b'not valid log content')]},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)

    def test_timestamp_parsing(self):
        timestamp = parse_timestamp('2026-10-30 10:15:30')
        self.assertIsNotNone(timestamp)
        self.assertEqual(timestamp.strftime('%Y-%m-%d %H:%M:%S'), '2026-10-30 10:15:30')

    def test_severity_extraction(self):
        self.assertEqual(normalize_severity('error'), 'ERROR')
        self.assertEqual(normalize_severity('warn'), 'WARNING')

    def test_request_id_extraction(self):
        self.assertEqual(extract_request_id('Payment request received request_id=req-101'), 'req-101')
        self.assertEqual(extract_request_id('Database connection failed requestId=abc-88'), 'abc-88')

    def test_event_filtering(self):
        investigation = Investigation.objects.create(name='Filter check')
        LogEvent.objects.create(
            investigation=investigation,
            timestamp='2026-10-30T10:15:30Z',
            severity='ERROR',
            service_name='payment-service',
            message='Database connection failed',
            request_id='req-101',
            source_file='sample.log',
            raw_log='test',
        )
        LogEvent.objects.create(
            investigation=investigation,
            timestamp='2026-10-30T10:16:30Z',
            severity='INFO',
            service_name='billing-service',
            message='Payment completed',
            request_id='req-102',
            source_file='sample.log',
            raw_log='test',
        )

        response = self.client.get(f'/api/investigations/{investigation.id}/events/?severity=ERROR')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

        filtered = self.client.get(f'/api/investigations/{investigation.id}/events/?service=payment')
        self.assertEqual(filtered.json()['count'], 1)

    def test_event_correlation(self):
        investigation = Investigation.objects.create(name='Correlation test')
        LogEvent.objects.create(
            investigation=investigation,
            timestamp='2026-10-30T10:15:30Z',
            severity='INFO',
            service_name='payment-service',
            message='Request started',
            request_id='req-100',
            source_file='sample.log',
            raw_log='test',
        )
        LogEvent.objects.create(
            investigation=investigation,
            timestamp='2026-10-30T10:15:35Z',
            severity='ERROR',
            service_name='database-service',
            message='Connection failed',
            request_id='req-100',
            source_file='sample.log',
            raw_log='test',
        )

        response = self.client.get(f'/api/investigations/{investigation.id}/correlations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_export_formats(self):
        investigation = Investigation.objects.create(name='Export case')
        LogEvent.objects.create(
            investigation=investigation,
            timestamp='2026-10-30T10:15:30Z',
            severity='ERROR',
            service_name='payment-service',
            message='Database disconnected',
            request_id='req-999',
            source_file='sample.log',
            raw_log='test',
        )

        csv_response = self.client.get(f'/api/investigations/{investigation.id}/export/?format=csv')
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn('req-999', csv_response.content.decode('utf-8'))

        json_response = self.client.get(f'/api/investigations/{investigation.id}/export/?format=json')
        self.assertEqual(json_response.status_code, 200)
        payload = json.loads(json_response.content.decode('utf-8'))
        self.assertEqual(payload['investigation']['name'], 'Export case')

    @staticmethod
    def _make_file(name, content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name=name, content=content, content_type='text/plain')


class ServiceParsingTests(TestCase):
    def test_parse_log_content(self):
        payload = parse_log_content(
            '2026-10-30 10:15:30 INFO [payment-service] Payment request received request_id=req-101\n'
            '2026-10-30 10:15:32 ERROR [payment-service] Database connection failed request_id=req-101',
            'sample.log',
        )
        self.assertEqual(payload['parsed_events'], 2)
        self.assertEqual(payload['severity_counts']['ERROR'], 1)
