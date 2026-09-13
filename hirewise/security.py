import base64
import hashlib
from datetime import timedelta
from functools import wraps

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone

from .models import AuditEvent, Membership, RateLimit


def cipher():
    key = settings.MFA_ENCRYPTION_KEY
    if not key and settings.ENVIRONMENT == 'development':
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def audit(request, action, entity=None, company=None, reason='', **metadata):
    metadata['actor_role'] = request.user.role if request.user.is_authenticated else 'guest'
    return AuditEvent.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        company=company, action=action, entity_type=entity.__class__.__name__ if entity else '',
        entity_id=str(entity.pk) if entity else '', reason=reason, metadata=metadata,
        correlation_id=request.correlation_id,
    )


def throttle(identity, limit=10, seconds=900):
    key = hashlib.sha256(identity.encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        row, _ = RateLimit.objects.get_or_create(key=key, defaults={'expires_at': now + timedelta(seconds=seconds)})
        row = RateLimit.objects.select_for_update().get(pk=row.pk)
        if row.expires_at <= now:
            row.count = 0
            row.expires_at = now + timedelta(seconds=seconds)
        row.count += 1
        row.save()
        return row.count > limit


def require_role(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not request.user.email_verified:
                return redirect('verification_pending')
            if request.user.role not in roles:
                raise PermissionDenied
            if request.user.role == 'admin' and (
                not request.user.mfa_enabled or request.session.get('mfa_user') != str(request.user.pk)
            ):
                return redirect('mfa')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def company_ids(user):
    return Membership.objects.filter(user=user, active=True).exclude(company__status='suspended').values_list('company_id', flat=True)
