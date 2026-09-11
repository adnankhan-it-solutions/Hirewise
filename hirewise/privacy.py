from django.db import transaction
from django.utils import timezone

from .documents import delete_document
from .models import Application, AuditEvent, Notification


def anonymize_application(application_id, reason):
    """Erase application content; retain minimal non-identifying lifecycle records."""
    with transaction.atomic():
        item = Application.objects.select_for_update().get(pk=application_id)
        if item.legal_hold:
            raise ValueError('legal_hold')
        if item.anonymized_at:
            return False
        for document in item.documents.all():
            delete_document(document)
        item.documents.all().delete()
        item.screenings.all().delete()
        item.interviews.all().delete()
        item.notes.all().delete()
        # Free-text human reasons may contain personal information.
        item.history.all().update(reason='Content removed under retention/privacy policy', actor=None)
        Notification.objects.filter(recipient=item.email, sent_at=None).delete()
        item.name = 'Removed candidate'
        item.email = f'removed-{item.pk}@example.invalid'
        item.cover_letter = ''
        item.screening_answer = ''
        item.profile_url = ''
        item.candidate = None
        item.assigned_to = None
        item.guest_token_hash = ''
        item.guest_token_expires = None
        item.email_verified = False
        item.stage = 'archived'
        item.anonymized_at = timezone.now()
        item.save()
        AuditEvent.objects.create(company=item.job.company, action='privacy.application_anonymized', entity_type='Application', entity_id=str(item.pk), reason=reason)
        return True
