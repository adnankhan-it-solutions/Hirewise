import hashlib
import secrets
import time
import uuid
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CompanyForm, MFAForm, PrivacyForm, ProfileForm, RegistrationForm
from .models import AuditEvent, CandidateProfile, Company, EmailToken, Membership, Notification, PrivacyRequest, User
from .security import audit, cipher, company_ids, require_role, throttle


def home(request):
    return render(request, 'home.html')


def info(request, page):
    pages = {
        'about': ('Recruitment with a clearer view', 'Hirewise brings job applications, evidence-based screening and human review into one workspace. Built for teams hiring in Qatar, with privacy at the centre.'),
        'how-it-works': ('A considered path from application to offer', 'Employers publish roles and review applications. Candidates share only relevant information. Screening provides evidence and highlights unknowns. Recruiters remain responsible for every hiring decision.'),
        'employers': ('Build your next great team', 'Create a company workspace, define your requirements, and review applicants in a private recruitment pipeline. Company approval is required before publishing.'),
        'candidates': ('Your next chapter starts here', 'Explore opportunities and apply with or without an account. Your documents are private. You control your applications and can request access, correction or deletion of your information.'),
        'privacy': ('Privacy and candidate information', 'Development notice v1 — pending legal review. We process account details and information you choose to submit for recruitment. Relevant employers can access their applications; unrelated employers cannot. External profiles are stored as links and are not scraped. AI processing, when enabled, assists human review. Use your privacy centre for access, correction, export or deletion requests. Production controller identity, retention periods, providers and transfer details must be approved and published before real candidate intake.'),
        'terms': ('Terms of use', 'Pre-launch draft — pending legal review. Submit accurate, job-related information. Employers must have authority to represent their company and use applications only for the disclosed recruitment purpose. Do not submit discriminatory or fraudulent vacancies. Screening is decision support; authorized humans make employment decisions. Final legal entity, service and payment terms require owner and counsel approval before launch.'),
        'cookies': ('Essential cookies only', 'This application uses session cookies for sign-in and security cookies to protect forms against cross-site requests. No advertising or third-party tracking cookies are installed.'),
        'security': ('Private by design', 'Company-scoped access, protected sessions, administrator MFA and recruitment audit histories help protect information. Documents are never served from a public upload directory. This pre-launch application is undergoing verification and has not been independently security certified.'),
        'contact': ('Let’s talk', f'For platform enquiries, contact {settings.SUPPORT_EMAIL}.' if settings.SUPPORT_EMAIL else 'The owner has not configured a public support address yet. Registered users can submit data requests through the privacy centre.'),
    }
    if page not in pages:
        from django.http import Http404
        raise Http404
    title, body = pages[page]
    return render(request, 'info.html', {'title': title, 'body': body})


def send_verification(user):
    raw = secrets.token_urlsafe(32)
    EmailToken.objects.create(user=user, digest=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now() + timedelta(hours=24))
    Notification.objects.create(user=user, recipient=user.email, subject='Verify your email',
                                body=f'Verify your email within 24 hours: {settings.PUBLIC_ORIGIN}/accounts/verify/{raw}/')


def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST':
        if throttle(f'register:{request.META.get("REMOTE_ADDR")}', 8):
            return HttpResponse('Please try again later.', status=429)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.username = str(uuid.uuid4())
                user.save()
                if user.role == 'candidate':
                    CandidateProfile.objects.create(user=user)
                send_verification(user)
                login(request, user)
                audit(request, 'account.registered', user)
            return redirect('verification_pending')
    return render(request, 'form.html', {'form': form, 'title': 'Create your account', 'subtitle': 'A better recruitment experience starts here.', 'button': 'Create account'})


def sign_in(request):
    form = AuthenticationForm(request, data=request.POST or None)
    form.fields['username'].label = 'Email address'
    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        limited_ip = throttle(f'login-ip:{request.META.get("REMOTE_ADDR")}', 40)
        limited_account = throttle(f'login-account:{email}', 10)
        if limited_ip or limited_account:
            audit(request, 'security.login_throttled')
            return HttpResponse('Too many attempts. Try again in 15 minutes.', status=429)
        user = User.objects.filter(email__iexact=email).first()
        authenticated = authenticate(request, username=user.username if user else email, password=request.POST.get('password', ''))
        if authenticated:
            login(request, authenticated)
            audit(request, 'account.login', authenticated)
            return redirect('mfa' if authenticated.role == 'admin' else 'dashboard')
        audit(request, 'security.login_failed')
        form.add_error(None, 'Unable to sign in with those credentials.')
    return render(request, 'form.html', {'form': form, 'title': 'Welcome back', 'subtitle': 'Sign in to your Hirewise workspace.', 'button': 'Sign in', 'login_page': True})


@require_POST
def sign_out(request):
    audit(request, 'account.logout')
    logout(request)
    return redirect('home')


@login_required
def verification_pending(request):
    if request.method == 'POST' and not request.user.email_verified:
        if throttle(f'verification:{request.user.pk}', 3, 3600):
            return HttpResponse('Please try again later.', status=429)
        send_verification(request.user)
        messages.success(request, 'A verification email has been queued.')
    return render(request, 'verify.html')


def verify_email(request, token):
    record = get_object_or_404(EmailToken, digest=hashlib.sha256(token.encode()).hexdigest(), purpose='verify')
    if record.used_at or record.expires_at <= timezone.now():
        return HttpResponse('This verification link has expired or has already been used.', status=400)
    if request.method == 'POST':
        with transaction.atomic():
            record = EmailToken.objects.select_for_update().get(pk=record.pk)
            if record.used_at or record.expires_at <= timezone.now():
                return HttpResponse('This link is no longer valid.', status=400)
            record.user.email_verified = True
            record.user.save(update_fields=['email_verified'])
            record.used_at = timezone.now()
            record.save(update_fields=['used_at'])
            audit(request, 'account.email_verified', record.user)
        messages.success(request, 'Email verified. You can now sign in and continue.')
        return redirect('dashboard' if request.user.is_authenticated else 'login')
    return render(request, 'confirm.html', {'title': 'Verify your email', 'body': 'Confirm that you requested this email verification.', 'button': 'Verify email'})


@login_required
def mfa(request):
    if request.user.role != 'admin':
        raise PermissionDenied
    form = MFAForm(request.POST or None)
    setup = not request.user.mfa_enabled
    if setup and 'pending_mfa' not in request.session:
        request.session['pending_mfa'] = pyotp.random_base32()
    secret = request.session.get('pending_mfa') if setup else cipher().decrypt(request.user.mfa_secret.encode()).decode()
    if request.method == 'POST':
        if throttle(f'mfa:{request.user.pk}', 8):
            return HttpResponse('Please try again later.', status=429)
        if form.is_valid():
            counter = int(time.time()) // 30
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                if counter > user.mfa_last_counter and pyotp.TOTP(secret).verify(form.cleaned_data['code'], valid_window=0):
                    user.mfa_secret = cipher().encrypt(secret.encode()).decode()
                    user.mfa_enabled = True
                    user.mfa_last_counter = counter
                    user.save(update_fields=['mfa_secret', 'mfa_enabled', 'mfa_last_counter'])
                    request.session.cycle_key()
                    request.session['mfa_user'] = str(user.pk)
                    request.session.pop('pending_mfa', None)
                    audit(request, 'account.mfa_verified', user)
                    return redirect('dashboard')
            form.add_error('code', 'Invalid or already-used code. Wait for a new code and try again.')
    return render(request, 'form.html', {'form': form, 'title': 'Secure administrator access', 'button': 'Verify authenticator',
                                       'subtitle': 'Enter a code from your authenticator app.', 'mfa_secret': secret if setup else None})


@require_role('candidate', 'recruiter', 'admin')
def dashboard(request):
    context = {}
    if request.user.role == 'recruiter':
        context['companies'] = Company.objects.filter(pk__in=company_ids(request.user))
    elif request.user.role == 'admin':
        context.update(company_count=Company.objects.count(), user_count=User.objects.count(),
                       pending_companies=Company.objects.filter(status='pending')[:20],
                       events=AuditEvent.objects.select_related('actor')[:15],
                       privacy_requests=PrivacyRequest.objects.select_related('user').filter(status='received')[:20])
    return render(request, 'dashboard.html', context)


@require_role('recruiter')
def company_create(request):
    form = CompanyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            company = form.save()
            Membership.objects.create(user=request.user, company=company, role='owner')
            audit(request, 'company.created', company, company)
        return redirect('dashboard')
    return render(request, 'form.html', {'form': form, 'title': 'Create your company', 'subtitle': 'Your workspace is private to your authorized recruiting team.', 'button': 'Create company'})


@require_role('recruiter')
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk, pk__in=company_ids(request.user))
    return render(request, 'info.html', {'title': company.name, 'body': company.description, 'status': company.get_status_display()})


@require_role('admin')
@require_POST
def company_moderate(request, pk):
    company = get_object_or_404(Company, pk=pk)
    status = request.POST.get('status')
    reason = request.POST.get('reason', '').strip()
    if status not in ('approved', 'suspended') or not reason or len(reason) > 2000:
        return HttpResponse('A valid status and reason are required.', status=400)
    with transaction.atomic():
        previous = company.status
        company.status = status
        company.save(update_fields=['status'])
        audit(request, 'company.moderated', company, company, reason, previous=previous, current=status)
    return redirect('dashboard')


@require_role('candidate')
def profile(request):
    instance, _ = CandidateProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            audit(request, 'candidate.profile_updated', instance)
        messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'form.html', {'form': form, 'title': 'Your professional profile', 'subtitle': 'Share job-related information. Profile links are never automatically scraped.', 'button': 'Save profile'})


@require_role('candidate', 'recruiter', 'admin')
def privacy(request):
    form = PrivacyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            audit(request, 'privacy.requested', item)
        messages.success(request, 'Your request has been recorded for authorized review.')
        return redirect('privacy_centre')
    return render(request, 'form.html', {'form': form, 'title': 'Your privacy centre', 'button': 'Submit request',
                                       'subtitle': 'Request access, a correction, an export or deletion. Your request will be reviewed against applicable obligations.',
                                       'requests': PrivacyRequest.objects.filter(user=request.user).order_by('-created_at')[:20]})


def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /accounts/\nDisallow: /dashboard/\nDisallow: /portal/\nDisallow: /applications/\nDisallow: /documents/\nDisallow: /interviews/\n', content_type='text/plain')
