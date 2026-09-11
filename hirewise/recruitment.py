import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .documents import read_document, store_document
from .forms import ApplicationForm, JobForm, RequirementForm
from .models import (Application, BackgroundTask, Consent, Document, Job, Notification,
                     PlatformConfig, RecruiterNote, StatusEvent)
from .security import audit, company_ids, require_role, throttle


def configuration():
    return PlatformConfig.objects.get_or_create(pk=1)[0]


def public_jobs():
    return Job.objects.filter(status='published', company__status='approved').filter(Q(deadline=None) | Q(deadline__gte=timezone.localdate()))


def jobs(request):
    query = public_jobs().select_related('company').order_by('-published_at')
    term = request.GET.get('q', '').strip()[:200]
    if term:
        query = query.filter(Q(title__icontains=term) | Q(description__icontains=term) | Q(company__name__icontains=term))
    workplace = request.GET.get('workplace', '')
    if workplace:
        query = query.filter(workplace=workplace)
    return render(request, 'jobs.html', {'page': Paginator(query, 12).get_page(request.GET.get('page')), 'query': term, 'workplace': workplace, 'title': 'Find your next chapter'})


def job_detail(request, pk):
    job = get_object_or_404(public_jobs().select_related('company'), pk=pk)
    return render(request, 'job_detail.html', {'job': job, 'title': job.title})


@require_role('recruiter')
def recruiter_jobs(request):
    query = Job.objects.filter(company_id__in=company_ids(request.user)).select_related('company').order_by('-created_at')
    return render(request, 'jobs.html', {'page': Paginator(query, 20).get_page(request.GET.get('page')), 'recruiter': True, 'title': 'Your vacancies'})


@require_role('recruiter')
def job_edit(request, pk=None):
    instance = get_object_or_404(Job, pk=pk, company_id__in=company_ids(request.user)) if pk else None
    form = JobForm(request.POST or None, user=request.user, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            job = form.save(commit=False)
            if not instance:
                job.created_by = request.user
            else:
                job.policy_version += 1
            # Any changed public content must pass moderation again.
            job.status = 'draft'
            job.save()
            audit(request, 'job.saved', job, job.company)
        return redirect('job_manage', pk=job.pk)
    return render(request, 'form.html', {'form': form, 'title': 'Edit vacancy' if instance else 'Create a vacancy', 'subtitle': 'Save your draft, then define objective screening criteria and submit for review.', 'button': 'Save draft'})


@require_role('recruiter')
def job_manage(request, pk):
    job = get_object_or_404(Job.objects.select_related('company'), pk=pk, company_id__in=company_ids(request.user))
    form = RequirementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            job = Job.objects.select_for_update().get(pk=job.pk)
            criterion = form.save(commit=False)
            criterion.job = job
            criterion.save()
            job.policy_version += 1
            job.status = 'draft'
            job.save(update_fields=['policy_version', 'status'])
            audit(request, 'job.criterion_added', criterion, job.company)
        return redirect('job_manage', pk=job.pk)
    return render(request, 'job_manage.html', {'job': job, 'form': form, 'title': job.title})


@require_role('recruiter')
@require_POST
def job_action(request, pk):
    with transaction.atomic():
        job = get_object_or_404(Job.objects.select_for_update(), pk=pk, company_id__in=company_ids(request.user))
        action = request.POST.get('action')
        if action == 'duplicate':
            criteria = list(job.criteria.values('label', 'category', 'mandatory', 'weight'))
            job.pk = None
            job._state.adding = True
            job.title = f'{job.title[:165]} (copy)'
            job.status = 'draft'
            job.published_at = None
            job.created_at = timezone.now()
            job.save()
            for criterion in criteria:
                job.criteria.create(**criterion)
            audit(request, 'job.duplicated', job, job.company)
            return redirect('job_manage', pk=job.pk)
        allowed = {'submit': 'pending', 'pause': 'paused', 'close': 'closed', 'archive': 'archived'}
        if action not in allowed:
            return HttpResponse('Invalid action.', status=400)
        if action == 'submit':
            if job.company.status != 'approved':
                messages.error(request, 'Your company must be approved before publication.')
                return redirect('job_manage', pk=job.pk)
            if configuration().payments_required:
                from .models import Entitlement
                if not Entitlement.objects.filter(job=job, active=True, sandbox=False).exists():
                    messages.error(request, 'A verified live posting entitlement is required. Sandbox purchases cannot publish paid jobs.')
                    return redirect('job_manage', pk=job.pk)
        previous = job.status
        job.status = allowed[action]
        job.save(update_fields=['status'])
        audit(request, 'job.status_changed', job, job.company, previous=previous, current=job.status)
    return redirect('job_manage', pk=job.pk)


@require_role('admin')
def moderation(request):
    if request.method == 'POST':
        job = get_object_or_404(Job, pk=request.POST.get('job'))
        reason = request.POST.get('reason', '').strip()[:2000]
        status = request.POST.get('status')
        if status not in ('published', 'paused', 'closed') or not reason:
            return HttpResponse('Status and review reason are required.', status=400)
        if status == 'published' and job.company.status != 'approved':
            return HttpResponse('Company approval is required.', status=400)
        if status == 'published' and configuration().payments_required:
            from .models import Entitlement
            if not Entitlement.objects.filter(job=job, active=True, sandbox=False).exists():
                return HttpResponse('A verified live entitlement is required.', status=400)
        with transaction.atomic():
            job.status = status
            if status == 'published':
                job.published_at = timezone.now()
            job.save(update_fields=['status', 'published_at'])
            audit(request, 'job.moderated', job, job.company, reason, status=status)
        return redirect('moderation')
    return render(request, 'moderation.html', {'page': Paginator(Job.objects.select_related('company').order_by('-created_at'), 20).get_page(request.GET.get('page')), 'title': 'Job moderation'})


def apply(request, pk):
    job = get_object_or_404(public_jobs(), pk=pk)
    config = configuration()
    if settings.ENVIRONMENT != 'development' and not config.production_intake_enabled:
        return HttpResponse('Applications are not open while launch verification is in progress.', status=503)
    if request.user.is_authenticated and (request.user.role != 'candidate' or not request.user.email_verified):
        raise PermissionDenied
    initial = {'email': request.user.email, 'name': request.user.get_full_name()} if request.user.is_authenticated else {}
    form = ApplicationForm(request.POST or None, request.FILES or None, initial=initial)
    if request.user.is_authenticated:
        form.fields['email'].disabled = True
    if not job.screening_question:
        form.fields.pop('screening_answer', None)
    else:
        form.fields['screening_answer'].label = job.screening_question
    if request.method == 'POST':
        if throttle(f'apply:{request.META.get("REMOTE_ADDR")}', 15, 3600):
            return HttpResponse('Application limit reached. Please try again later.', status=429)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Recheck publication while holding the vacancy lock.
                    job = get_object_or_404(public_jobs().select_for_update(), pk=pk)
                    item = form.save(commit=False)
                    item.job = job
                    item.expires_at = timezone.now() + timedelta(days=config.retention_days)
                    raw = secrets.token_urlsafe(32)
                    if request.user.is_authenticated:
                        item.candidate = request.user
                        item.email = request.user.email.lower()
                        item.email_verified = True
                    else:
                        item.guest_token_hash = hashlib.sha256(raw.encode()).hexdigest()
                        item.guest_token_expires = timezone.now() + timedelta(days=2)
                    item.save()
                    document = Document.objects.create(application=item, **store_document(form.cleaned_data['cv']))
                    BackgroundTask.objects.create(document=document)
                    Consent.objects.create(application=item, purpose='recruitment_processing', notice_version=config.notice_version)
                    StatusEvent.objects.create(application=item, actor=request.user if request.user.is_authenticated else None, current='received', reason='Application submitted')
                    audit(request, 'application.submitted', item, job.company)
                    link = f'{settings.PUBLIC_ORIGIN}/applications/{item.pk}/' if item.candidate else f'{settings.PUBLIC_ORIGIN}/applications/guest/{item.pk}/{raw}/'
                    Notification.objects.create(user=item.candidate, recipient=item.email, subject=f'Application received: {job.title}', body=f'Your reference is {item.reference}. Verify/view your application: {link}\nYour application is saved. Screening assists human review.')
                request.session['submission_reference'] = item.reference
                return redirect('application_received')
            except IntegrityError:
                form.add_error(None, 'A verified application already exists for this vacancy and email.')
            except ValidationError as exc:
                form.add_error('cv', exc)
    return render(request, 'form.html', {'form': form, 'title': f'Apply for {job.title}', 'subtitle': f'{job.company.name} · Read the processing notice before submitting. Guest applicants receive a private verification link by email.', 'button': 'Submit application', 'application_notice': True})


def application_received(request):
    reference = request.session.pop('submission_reference', None)
    if not reference:
        return redirect('jobs')
    return render(request, 'info.html', {'title': 'Your application is received', 'body': f'Your reference: {reference}\nWe have saved your application. Check your email for your private confirmation link. Recruitment decisions are made by authorized people.'})


def candidate_scope(request):
    if request.user.is_authenticated and request.user.role == 'candidate' and request.user.email_verified:
        return Application.objects.filter(candidate=request.user, anonymized_at=None)
    guest_id = request.session.get('guest_application')
    expiry = request.session.get('guest_expiry', 0)
    if guest_id and expiry > timezone.now().timestamp():
        return Application.objects.filter(pk=guest_id, email_verified=True, anonymized_at=None)
    return Application.objects.none()


def authorized_application(request, pk):
    if request.user.is_authenticated and request.user.role in ('recruiter', 'admin'):
        if not request.user.email_verified:
            raise PermissionDenied
        if request.user.role == 'admin':
            # Admin candidate access uses a separate support workflow with justification.
            raise PermissionDenied
        return get_object_or_404(Application.objects.select_related('job__company'), pk=pk, job__company_id__in=company_ids(request.user), email_verified=True, anonymized_at=None), True
    return get_object_or_404(candidate_scope(request).select_related('job__company'), pk=pk), False


def guest_verify(request, pk, token):
    item = get_object_or_404(Application, pk=pk, anonymized_at=None)
    expected = hashlib.sha256(token.encode()).hexdigest()
    if not secrets.compare_digest(expected, item.guest_token_hash) or not item.guest_token_expires or item.guest_token_expires < timezone.now():
        raise Http404
    if request.method == 'POST':
        try:
            with transaction.atomic():
                item = Application.objects.select_for_update().get(pk=item.pk)
                if not secrets.compare_digest(expected, item.guest_token_hash):
                    raise Http404
                item.email_verified = True
                if request.user.is_authenticated and request.user.role == 'candidate' and request.user.email_verified and request.user.email.lower() == item.email:
                    item.candidate = request.user
                item.guest_token_hash = ''
                item.save(update_fields=['email_verified', 'candidate', 'guest_token_hash'])
                audit(request, 'application.email_verified', item, item.job.company)
        except IntegrityError:
            return HttpResponse('A verified application already exists. Sign in to manage it or contact support.', status=409)
        request.session.cycle_key()
        request.session['guest_application'] = str(item.pk)
        request.session['guest_expiry'] = (timezone.now() + timedelta(hours=2)).timestamp()
        return redirect('application_detail', pk=item.pk)
    return render(request, 'confirm.html', {'title': 'Open your private application', 'body': 'Verify your email and open a two-hour private session for this application. This link can be used once.', 'button': 'Verify and continue'})


@require_role('candidate', 'recruiter')
def applications(request):
    recruiter = request.user.role == 'recruiter'
    query = Application.objects.filter(job__company_id__in=company_ids(request.user), email_verified=True, anonymized_at=None) if recruiter else candidate_scope(request)
    query = query.select_related('job__company').order_by('-created_at')
    term = request.GET.get('q', '').strip()[:150]
    if term:
        query = query.filter(Q(job__title__icontains=term) | Q(name__icontains=term))
    stage = request.GET.get('stage')
    if stage:
        query = query.filter(stage=stage)
    return render(request, 'applications.html', {'page': Paginator(query, 20).get_page(request.GET.get('page')), 'recruiter': recruiter, 'blind': configuration().blind_review and recruiter, 'query': term, 'stages': Application.STAGES, 'title': 'Applications'})


def application_detail(request, pk):
    item, recruiter = authorized_application(request, pk)
    if request.method == 'POST':
        if not recruiter:
            raise PermissionDenied
        note = request.POST.get('note', '').strip()
        if not note or len(note) > 5000:
            return HttpResponse('A note of up to 5,000 characters is required.', status=400)
        with transaction.atomic():
            record = RecruiterNote.objects.create(application=item, author=request.user, text=note)
            audit(request, 'application.note_added', record, item.job.company)
        return redirect('application_detail', pk=item.pk)
    audit(request, 'application.viewed', item, item.job.company)
    return render(request, 'application_detail.html', {'item': item, 'recruiter': recruiter, 'blind': configuration().blind_review and recruiter,
                 'history': item.history.select_related('actor'), 'notes': item.notes.select_related('author') if recruiter else [],
                 'screenings': item.screenings.order_by('-created_at'), 'stages': Application.STAGES, 'title': 'Application review'})


@require_POST
def application_transition(request, pk):
    item, recruiter = authorized_application(request, pk)
    stage = request.POST.get('stage')
    reason = request.POST.get('reason', '').strip()
    valid = dict(Application.STAGES)
    if stage not in valid or not reason or len(reason) > 2000:
        return HttpResponse('A valid stage and reason are required.', status=400)
    if not recruiter and stage != 'withdrawn':
        raise PermissionDenied
    with transaction.atomic():
        item = Application.objects.select_for_update().get(pk=item.pk)
        if item.stage in ('withdrawn', 'archived'):
            return HttpResponse('This application is closed to further transitions.', status=409)
        previous = item.stage
        if previous == stage:
            return redirect('application_detail', pk=item.pk)
        item.stage = stage
        item.save(update_fields=['stage'])
        StatusEvent.objects.create(application=item, actor=request.user if request.user.is_authenticated else None, previous=previous, current=stage, reason=reason)
        audit(request, 'application.stage_changed', item, item.job.company, reason, previous=previous, current=stage)
        Notification.objects.create(user=item.candidate, recipient=item.email, subject='Application status updated', body=f'{item.reference}: {item.get_stage_display()}. Sign in to your workspace to view your application. Internal reviewer comments are private.')
    return redirect('application_detail', pk=item.pk)


def document_link(request, pk):
    document = get_object_or_404(Document.objects.select_related('application'), pk=pk)
    authorized_application(request, document.application_id)
    if document.scan_status != 'clean':
        return HttpResponse('Document access is unavailable until malware scanning succeeds.', status=409)
    token = signing.dumps({'document': str(document.pk), 'session': request.session.session_key}, salt='private-document')
    audit(request, 'document.link_issued', document, document.application.job.company)
    return redirect('document_download', token=token)


def document_download(request, token):
    try:
        payload = signing.loads(token, salt='private-document', max_age=120)
    except signing.BadSignature:
        raise Http404
    if payload['session'] != request.session.session_key:
        raise Http404
    document = get_object_or_404(Document, pk=payload['document'], scan_status='clean')
    authorized_application(request, document.application_id)
    data = read_document(document)
    if hashlib.sha256(data).hexdigest() != document.sha256:
        return HttpResponse('Document integrity verification failed.', status=409)
    audit(request, 'document.downloaded', document, document.application.job.company)
    response = HttpResponse(data, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="cv-{document.pk}{document.extension}"'
    response['Cache-Control'] = 'no-store, private'
    return response
