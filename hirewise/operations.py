import csv
import hashlib
import secrets
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ConfigForm
from .matching import screen
from .models import (Application, AuditEvent, Company, Job, Membership, Notification, Price,
                     PrivacyRequest, TeamInvitation)
from .payments import owner_companies
from .recruitment import authorized_application, candidate_scope, configuration
from .security import audit, company_ids, require_role, throttle


@require_role('recruiter')
@require_POST
def rescreen(request, pk):
    application, _ = authorized_application(request, pk)
    if throttle(f'rescreen:{request.user.pk}', 30, 3600):
        return HttpResponse('Please try again later.', status=429)
    with transaction.atomic():
        run = screen(application)
        audit(request, 'screening.re_evaluated', run, application.job.company, policy=run.policy_snapshot['version'])
    return redirect('application_detail', pk=pk)


@require_role('recruiter')
def candidate_report(request, pk):
    application, _ = authorized_application(request, pk)
    audit(request, 'report.exported', application, application.job.company, format='html-printable')
    return render(request, 'report.html', {'item': application, 'screenings': application.screenings.order_by('-created_at'),
                  'events': AuditEvent.objects.filter(company=application.job.company, entity_id=str(application.pk)).order_by('created_at'),
                  'title': 'Candidate evidence report'})


@require_role('recruiter')
def analytics(request):
    query = Application.objects.filter(job__company_id__in=company_ids(request.user), email_verified=True, anonymized_at=None)
    job = request.GET.get('job')
    if job:
        try:
            query = query.filter(job_id=job)
        except (ValueError, forms.ValidationError):
            raise Http404
    total = query.count()
    counts = list(query.values('stage').annotate(count=Count('id')).order_by('stage'))
    return render(request, 'analytics.html', {'total': total, 'counts': counts, 'jobs': Job.objects.filter(company_id__in=company_ids(request.user)),
                 'hires': query.filter(stage='hired').count(), 'shortlisted': query.filter(stage='shortlisted').count(), 'title': 'Recruitment analytics'})


@require_role('recruiter')
def export_csv(request):
    rows = Application.objects.filter(job__company_id__in=owner_companies(request.user), email_verified=True, anonymized_at=None).select_related('job').order_by('-created_at')[:5000]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="recruitment-summary.csv"'
    writer = csv.writer(response)
    writer.writerow(['Reference', 'Job', 'Stage', 'Submitted UTC'])
    for row in rows:
        values = [row.reference, row.job.title, row.stage, row.created_at.isoformat()]
        writer.writerow(["'" + x if x.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else x for x in values])
    audit(request, 'report.summary_exported', format='csv', limit=5000)
    return response


@require_role('admin')
def settings_view(request):
    config = configuration()
    form = ConfigForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            audit(request, 'platform.configuration_changed', config, changed=form.changed_data)
        messages.success(request, 'Platform settings saved. Existing scoring and invoice snapshots remain unchanged.')
        return redirect('platform_settings')
    return render(request, 'form.html', {'form': form, 'title': 'Platform configuration', 'button': 'Save configuration', 'subtitle': 'Production intake requires a separate deployment launch review; it cannot be enabled through this form.'})


class PriceForm(forms.ModelForm):
    class Meta:
        model = Price
        fields = ['name', 'description', 'amount_minor', 'currency', 'active']


@require_role('admin')
def prices(request):
    form = PriceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            price = form.save()
            audit(request, 'pricing.created', price)
        return redirect('pricing')
    return render(request, 'form.html', {'form': form, 'title': 'Add a pricing package', 'subtitle': 'Enter integer minor units: 100 means 1.00 in the selected currency. This creates an internal sandbox package.', 'button': 'Create package'})


@require_role('admin')
def audit_log(request):
    events = AuditEvent.objects.order_by('-created_at')
    action = request.GET.get('q', '').strip()[:100]
    if action:
        events = events.filter(action__icontains=action)
    return render(request, 'audit.html', {'page': Paginator(events, 50).get_page(request.GET.get('page')), 'query': action, 'title': 'Audit log'})


@require_role('candidate')
def own_export(request):
    applications = []
    for item in candidate_scope(request).prefetch_related('history', 'interviews__questions__answer')[:1000]:
        applications.append({'reference': item.reference, 'job': item.job.title, 'name': item.name, 'email': item.email,
                             'cover_letter': item.cover_letter, 'screening_answer': item.screening_answer, 'stage': item.stage,
                             'submitted_at': item.created_at.isoformat(),
                             'history': [{'stage': e.current, 'at': e.created_at.isoformat()} for e in item.history.all()],
                             'interviews': [{'id': str(i.pk), 'answers': [{'question': q.text, 'answer': getattr(getattr(q, 'answer', None), 'text', '')} for q in i.questions.all()]} for i in item.interviews.all()]})
    # Internal notes, recruiter rationales and third-party records are never serialized.
    audit(request, 'privacy.self_exported', request.user)
    response = JsonResponse({'email': request.user.email, 'name': request.user.get_full_name(), 'applications': applications})
    response['Content-Disposition'] = 'attachment; filename="my-hirewise-data.json"'
    return response


@require_role('admin')
def privacy_queue(request):
    if request.method == 'POST':
        item = get_object_or_404(PrivacyRequest, pk=request.POST.get('request'))
        status = request.POST.get('status')
        resolution = request.POST.get('resolution', '').strip()[:5000]
        if status not in ('in_review', 'fulfilled', 'declined') or not resolution:
            return HttpResponse('Status and resolution are required.', status=400)
        with transaction.atomic():
            item.status = status
            item.resolution = resolution
            item.save(update_fields=['status', 'resolution'])
            audit(request, 'privacy.reviewed', item, reason=resolution, status=status)
        return redirect('privacy_queue')
    return render(request, 'privacy_queue.html', {'page': Paginator(PrivacyRequest.objects.order_by('-created_at'), 30).get_page(request.GET.get('page')), 'title': 'Privacy request review'})


class InvitationForm(forms.Form):
    email = forms.EmailField()


@require_role('recruiter')
def invite_team(request, pk):
    company = get_object_or_404(Company, pk=pk, pk__in=owner_companies(request.user))
    form = InvitationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if throttle(f'team-invite:{request.user.pk}', 20, 3600):
            return HttpResponse(status=429)
        raw = secrets.token_urlsafe(32)
        with transaction.atomic():
            invitation = TeamInvitation.objects.create(company=company, email=form.cleaned_data['email'].lower(), digest=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now() + timedelta(days=7))
            Notification.objects.create(recipient=invitation.email, subject=f'Invitation to {company.name}', body=f'Create and verify a recruiter account using this email, then accept your invitation: {settings.PUBLIC_ORIGIN}/portal/team/accept/{raw}/')
            audit(request, 'team.invited', invitation, company)
        messages.success(request, 'Team invitation queued for delivery.')
        return redirect('dashboard')
    return render(request, 'form.html', {'form': form, 'title': 'Invite a recruiting teammate', 'button': 'Send invitation'})


@require_role('recruiter')
def accept_team(request, token):
    invitation = get_object_or_404(TeamInvitation, digest=hashlib.sha256(token.encode()).hexdigest(), email=request.user.email.lower(), accepted_at=None, expires_at__gt=timezone.now(), company__status='approved')
    if request.method == 'POST':
        with transaction.atomic():
            invitation = TeamInvitation.objects.select_for_update().get(pk=invitation.pk)
            if invitation.accepted_at:
                raise Http404
            Membership.objects.get_or_create(user=request.user, company=invitation.company, defaults={'role': 'recruiter'})
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['accepted_at'])
            audit(request, 'team.joined', invitation, invitation.company)
        return redirect('dashboard')
    return render(request, 'confirm.html', {'title': f'Join {invitation.company.name}', 'body': 'You will gain recruiter access to this company’s vacancies and authorized applications.', 'button': 'Accept invitation'})


def guest_recover(request):
    form = InvitationForm(request.POST or None)
    if request.method == 'POST':
        if throttle(f'guest-recover:{request.META.get("REMOTE_ADDR")}', 5, 3600):
            return HttpResponse(status=429)
        if form.is_valid():
            for item in Application.objects.filter(email=form.cleaned_data['email'].lower(), candidate=None, anonymized_at=None).exclude(stage='archived')[:20]:
                raw = secrets.token_urlsafe(32)
                with transaction.atomic():
                    item.guest_token_hash = hashlib.sha256(raw.encode()).hexdigest()
                    item.guest_token_expires = timezone.now() + timedelta(hours=2)
                    item.save(update_fields=['guest_token_hash', 'guest_token_expires'])
                    Notification.objects.create(recipient=item.email, subject='Your private application link', body=f'{item.reference}\n{settings.PUBLIC_ORIGIN}/applications/guest/{item.pk}/{raw}/')
            return render(request, 'info.html', {'title': 'Check your email', 'body': 'If guest applications exist for that address, private access links have been queued.'})
    return render(request, 'form.html', {'form': form, 'title': 'Find your guest applications', 'button': 'Send private links'})
