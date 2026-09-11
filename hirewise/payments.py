"""Internal payment sandbox. This adapter never handles money or live entitlements."""
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Protocol

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Entitlement, Invoice, Job, Membership, Payment, PaymentEvent, Price
from .recruitment import configuration
from .security import audit, require_role


class PaymentProviderInterface(Protocol):
    def create_payment(self, payment): ...
    def verify_payment(self, payment): ...
    def refund_payment(self, payment): ...
    def receive_webhook(self, body, signature, timestamp): ...
    def verify_webhook(self, body, signature, timestamp): ...
    def get_transaction(self, reference): ...
    def get_settlement_status(self, payment): ...


class SandboxProvider:
    name = 'internal-sandbox'

    def secret(self):
        value = os.environ.get('SANDBOX_WEBHOOK_SECRET')
        if not value and settings.ENVIRONMENT == 'development':
            value = settings.SECRET_KEY + ':sandbox-only'
        if not value:
            raise ValueError('sandbox_disabled')
        return value.encode()

    def create_payment(self, payment):
        return {'reference': payment.provider_reference, 'sandbox': True, 'status': 'pending'}

    def verify_payment(self, payment):
        return {'status': payment.status, 'amount_minor': payment.amount_minor, 'currency': payment.currency, 'sandbox': True}

    def signature(self, body, timestamp):
        return hmac.new(self.secret(), str(timestamp).encode() + b'.' + body, hashlib.sha256).hexdigest()

    def verify_webhook(self, body, signature, timestamp):
        try:
            if abs(time.time() - int(timestamp)) > 300:
                return False
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(self.signature(body, timestamp), signature)

    def receive_webhook(self, body, signature, timestamp):
        if not self.verify_webhook(body, signature, timestamp):
            raise ValueError('invalid_signature_or_timestamp')
        payload = json.loads(body)
        if not isinstance(payload, dict) or set(payload) != {'event_id', 'reference', 'amount_minor', 'currency', 'status'}:
            raise ValueError('invalid_payload')
        if payload['status'] not in ('paid', 'failed') or type(payload['amount_minor']) is not int or not isinstance(payload['event_id'], str) or not 1 <= len(payload['event_id']) <= 100:
            raise ValueError('invalid_event')
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(provider_reference=payload['reference'], provider=self.name, sandbox=True)
            if payload['amount_minor'] != payment.amount_minor or payload['currency'] != payment.currency:
                raise ValueError('amount_or_currency_mismatch')
            digest = hashlib.sha256(body).hexdigest()
            existing = PaymentEvent.objects.filter(event_id=payload['event_id']).first()
            if existing:
                if existing.payment_id != payment.pk or existing.payload_hash != digest:
                    raise ValueError('conflicting_event')
                return payment
            if payment.status != 'pending':
                raise ValueError('terminal_payment')
            PaymentEvent.objects.create(payment=payment, event_id=payload['event_id'], status=payload['status'], payload_hash=digest)
            payment.status = payload['status']
            payment.save(update_fields=['status'])
            if payment.status == 'paid':
                Entitlement.objects.get_or_create(payment=payment, defaults={'job': payment.job, 'sandbox': True})
                config = configuration()
                Invoice.objects.get_or_create(payment=payment, defaults={'number': f'TEST-{payment.pk}', 'legal_snapshot': {'entity': config.legal_entity, 'address': config.legal_address, 'tax_reference': config.legal_tax_reference, 'customer': payment.company.name, 'sandbox': True}})
            from .models import AuditEvent
            AuditEvent.objects.create(company=payment.company, action='payment.sandbox_verified', entity_type='Payment', entity_id=str(payment.pk), metadata={'status': payment.status})
            return payment

    def refund_payment(self, payment):
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=payment.pk, sandbox=True)
            if payment.status != 'paid':
                raise ValueError('payment_not_paid')
            payment.status = 'refunded'
            payment.save(update_fields=['status'])
            Entitlement.objects.filter(payment=payment).update(active=False)
        return {'status': 'refunded', 'sandbox': True}

    def get_transaction(self, reference):
        return Payment.objects.get(provider_reference=reference, sandbox=True)

    def get_settlement_status(self, payment):
        return {'status': 'not_applicable', 'reason': 'Internal sandbox; no money collected.'}


def owner_companies(user):
    return Membership.objects.filter(user=user, active=True, role='owner').exclude(company__status='suspended').values_list('company_id', flat=True)


def pricing(request):
    return render(request, 'pricing.html', {'prices': Price.objects.filter(active=True), 'title': 'Simple, considered hiring'})


@require_role('recruiter')
def billing(request):
    query = Payment.objects.filter(company_id__in=owner_companies(request.user)).select_related('company', 'job').order_by('-created_at')
    from django.core.paginator import Paginator
    return render(request, 'billing.html', {'page': Paginator(query, 20).get_page(request.GET.get('page')), 'title': 'Payments and invoices'})


@require_role('recruiter')
def checkout(request, pk):
    job = get_object_or_404(Job, pk=pk, company_id__in=owner_companies(request.user))
    if request.method == 'POST':
        price = get_object_or_404(Price, pk=request.POST.get('price'), active=True)
        with transaction.atomic():
            payment = Payment.objects.create(company=job.company, job=job, price=price, user=request.user, amount_minor=price.amount_minor, currency=price.currency, item_description=price.name)
            SandboxProvider().create_payment(payment)
            audit(request, 'payment.sandbox_created', payment, job.company)
        return redirect('payment_detail', pk=payment.pk)
    return render(request, 'checkout.html', {'job': job, 'prices': Price.objects.filter(active=True), 'title': 'Sandbox checkout'})


@require_role('recruiter')
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk, company_id__in=owner_companies(request.user))
    return render(request, 'payment.html', {'payment': payment, 'title': 'Payment details'})


@require_role('recruiter')
@require_POST
def simulate_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk, company_id__in=owner_companies(request.user), sandbox=True)
    if settings.ENVIRONMENT != 'development':
        return HttpResponse('Interactive simulation is disabled outside development.', status=403)
    body = json.dumps({'event_id': secrets.token_hex(16), 'reference': str(payment.provider_reference), 'amount_minor': payment.amount_minor, 'currency': payment.currency, 'status': 'paid'}).encode()
    provider = SandboxProvider()
    stamp = str(int(time.time()))
    try:
        provider.receive_webhook(body, provider.signature(body, stamp), stamp)
    except ValueError:
        messages.error(request, 'This payment has already reached a final state.')
    return redirect('payment_detail', pk=pk)


@csrf_exempt
@require_POST
def sandbox_webhook(request):
    if len(request.body) > 8192:
        return HttpResponse(status=413)
    try:
        SandboxProvider().receive_webhook(request.body, request.headers.get('X-Signature', ''), request.headers.get('X-Timestamp', ''))
    except (ValueError, TypeError, KeyError, Payment.DoesNotExist):
        return JsonResponse({'error': 'invalid_event'}, status=400)
    return JsonResponse({'received': True})


@require_role('recruiter')
def invoice(request, pk):
    item = get_object_or_404(Invoice.objects.select_related('payment__company'), pk=pk, payment__company_id__in=owner_companies(request.user))
    audit(request, 'invoice.viewed', item, item.payment.company)
    from decimal import Decimal
    return render(request, 'invoice.html', {'invoice': item, 'amount': Decimal(item.payment.amount_minor) / 100, 'title': 'Test receipt'})
