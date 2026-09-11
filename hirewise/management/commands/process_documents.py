import hashlib
import json
import subprocess
import sys
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from hirewise.documents import read_document, scan_bytes
from hirewise.matching import screen
from hirewise.models import AuditEvent, BackgroundTask, Document, Extraction


class Command(BaseCommand):
    help = 'Process a bounded batch of quarantined CVs with scanner and isolated extraction.'

    def handle(self, *args, **options):
        now = timezone.now()
        ids = list(BackgroundTask.objects.filter(attempts__lt=8, available_at__lte=now).filter(Q(status='pending') | Q(status='running', leased_until__lt=now)).values_list('pk', flat=True)[:20])
        for pk in ids:
            with transaction.atomic():
                task = BackgroundTask.objects.select_for_update().get(pk=pk)
                if task.status not in ('pending', 'running') or (task.status == 'running' and task.leased_until and task.leased_until > timezone.now()):
                    continue
                task.status = 'running'
                task.attempts += 1
                task.leased_until = timezone.now() + timedelta(minutes=5)
                task.save()
            document = task.document
            try:
                data = read_document(document)
                if hashlib.sha256(data).hexdigest() != document.sha256:
                    raise ValueError('document_integrity')
                scan_status = scan_bytes(data)
                if scan_status == 'infected':
                    Document.objects.filter(pk=document.pk).update(scan_status='infected', processing_status='blocked', error_code='malware_detected')
                    BackgroundTask.objects.filter(pk=pk).update(status='blocked')
                    continue
                result = subprocess.run([sys.executable, '-m', 'hirewise.parser', document.extension], input=data, capture_output=True,
                                        timeout=30, check=True, cwd=settings.BASE_DIR,
                                        env={'PATH': '/usr/bin:/bin', 'PYTHONIOENCODING': 'utf-8'})
                sections = json.loads(result.stdout)
                if not isinstance(sections, list) or any(not isinstance(s, dict) or set(s) != {'section', 'text'} or not all(isinstance(v, str) for v in s.values()) for s in sections):
                    raise ValueError('invalid_extraction_schema')
                with transaction.atomic():
                    document = Document.objects.select_for_update().get(pk=document.pk)
                    if document.application.anonymized_at:
                        raise ValueError('application_removed')
                    document.scan_status = 'clean'
                    document.processing_status = 'complete' if sections else 'manual_review'
                    document.error_code = ''
                    document.save()
                    # Retry after a crash must not duplicate the same parser output.
                    Extraction.objects.get_or_create(document=document, parser_version='bounded-parser-v1', defaults={'sections': sections})
                    run = screen(document.application)
                    AuditEvent.objects.create(company=document.application.job.company, action='screening.completed', entity_type='ScreeningRun', entity_id=str(run.pk), metadata={'provider': run.provider})
                    BackgroundTask.objects.filter(pk=pk).update(status='complete')
            except Exception:
                # Never log CV content, parser stderr, or provider payloads.
                Document.objects.filter(pk=document.pk).update(processing_status='unavailable', error_code='processing_temporarily_unavailable')
                BackgroundTask.objects.filter(pk=pk).update(status='pending', available_at=timezone.now() + timedelta(minutes=min(2 ** task.attempts, 120)))
        self.stdout.write(f'Attempted {len(ids)} document tasks; check task/document status for outcomes.')
