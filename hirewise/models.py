import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        RECRUITER = 'recruiter', 'Recruiter'
        ADMIN = 'admin', 'Administrator'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)
    email_verified = models.BooleanField(default=False)
    mfa_secret = models.TextField(blank=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_last_counter = models.BigIntegerField(default=-1)

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='unique_email_case_insensitive')]


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True


class Company(Record):
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True, max_length=5000)
    country = models.CharField(max_length=2, default='QA')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending review'), ('approved', 'Approved'), ('suspended', 'Suspended')], default='pending')

    def __str__(self):
        return self.name


class Membership(Record):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[('owner', 'Owner'), ('recruiter', 'Recruiter')], default='recruiter')
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'company'], name='unique_company_member')]


class CandidateProfile(Record):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    headline = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True, max_length=5000)
    profile_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    notifications_enabled = models.BooleanField(default=True)


class EmailToken(Record):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=20, default='verify')
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)


class AuditEvent(Record):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    company = models.ForeignKey(Company, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    reason = models.TextField(blank=True, max_length=2000)
    metadata = models.JSONField(default=dict)
    correlation_id = models.UUIDField(default=uuid.uuid4)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['company', '-created_at']), models.Index(fields=['action', '-created_at'])]


class RateLimit(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class Notification(Record):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)


class PrivacyRequest(Record):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=[('access', 'Access'), ('correction', 'Correction'), ('export', 'Export'), ('deletion', 'Deletion')])
    details = models.TextField(max_length=3000, blank=True)
    status = models.CharField(max_length=20, default='received')
    resolution = models.TextField(blank=True)


class PlatformConfig(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    platform_name = models.CharField(max_length=100, default='Hirewise')
    support_email = models.EmailField(blank=True)
    legal_entity = models.CharField(max_length=200, blank=True)
    legal_address = models.TextField(blank=True)
    legal_tax_reference = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default='QAR')
    retention_days = models.PositiveIntegerField(default=180)
    payments_required = models.BooleanField(default=False)
    interviews_enabled = models.BooleanField(default=True)
    blind_review = models.BooleanField(default=True)
    notice_version = models.CharField(max_length=40, default='development-v1')
    production_intake_enabled = models.BooleanField(default=False)


class Job(Record):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    department = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, default='Doha')
    country = models.CharField(max_length=2, default='QA')
    workplace = models.CharField(max_length=12, choices=[('onsite', 'On-site'), ('hybrid', 'Hybrid'), ('remote', 'Remote')], default='onsite')
    employment = models.CharField(max_length=20, choices=[('full_time', 'Full-time'), ('part_time', 'Part-time'), ('contract', 'Contract')], default='full_time')
    seniority = models.CharField(max_length=80, blank=True)
    openings = models.PositiveIntegerField(default=1)
    description = models.TextField(max_length=20000)
    responsibilities = models.TextField(max_length=10000, blank=True)
    requirements_text = models.TextField(max_length=10000, blank=True)
    preferred_text = models.TextField(max_length=10000, blank=True)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='QAR')
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('pending', 'Pending review'), ('published', 'Published'), ('paused', 'Paused'), ('closed', 'Closed'), ('archived', 'Archived')], default='draft')
    interview_enabled = models.BooleanField(default=False)
    screening_question = models.CharField(max_length=500, blank=True)
    policy_version = models.PositiveIntegerField(default=1)
    published_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=['company', 'status']), models.Index(fields=['status', '-created_at'])]

    @property
    def reference(self):
        return f'JOB-{str(self.pk)[:8].upper()}'

    def __str__(self):
        return self.title


class Requirement(Record):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='criteria')
    label = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=[('skill', 'Skill'), ('experience', 'Experience'), ('education', 'Education'), ('certification', 'Certification'), ('language', 'Language'), ('preferred', 'Preferred')])
    mandatory = models.BooleanField(default=True)
    weight = models.PositiveIntegerField(default=10)


class Application(Record):
    STAGES = [(s, s.replace('_', ' ').title()) for s in ['received', 'under_review', 'ai_screening', 'interview_requested', 'interview_scheduled', 'interview_completed', 'human_review', 'shortlisted', 'employer_interview', 'offer', 'hired', 'rejected', 'withdrawn', 'archived']]
    job = models.ForeignKey(Job, on_delete=models.PROTECT)
    candidate = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=160)
    email = models.EmailField()
    email_verified = models.BooleanField(default=False)
    cover_letter = models.TextField(max_length=10000, blank=True)
    screening_answer = models.TextField(max_length=5000, blank=True)
    profile_url = models.URLField(blank=True)
    stage = models.CharField(max_length=30, choices=STAGES, default='received')
    guest_token_hash = models.CharField(max_length=64, blank=True)
    guest_token_expires = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
    legal_hold = models.BooleanField(default=False)
    anonymized_at = models.DateTimeField(null=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_applications')

    class Meta:
        indexes = [models.Index(fields=['job', 'stage', '-created_at']), models.Index(fields=['candidate', '-created_at'])]
        constraints = [models.UniqueConstraint(fields=['job', 'email'], condition=models.Q(email_verified=True, anonymized_at=None), name='unique_verified_application')]

    @property
    def reference(self):
        return f'APP-{self.created_at.year}-{str(self.pk).upper()}'


class Consent(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    notice_version = models.CharField(max_length=50)
    action = models.CharField(max_length=30, default='accepted')


class StatusEvent(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='history')
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    previous = models.CharField(max_length=30, blank=True)
    current = models.CharField(max_length=30)
    reason = models.TextField(max_length=2000, blank=True)

    class Meta:
        ordering = ['created_at']


class RecruiterNote(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    text = models.TextField(max_length=5000)


class Document(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    storage_key = models.CharField(max_length=300)
    extension = models.CharField(max_length=8)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    scan_status = models.CharField(max_length=30, default='quarantined')
    processing_status = models.CharField(max_length=30, default='pending')
    error_code = models.CharField(max_length=80, blank=True)


class Extraction(Record):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='extractions')
    parser_version = models.CharField(max_length=60)
    sections = models.JSONField(default=list)
    confidence = models.CharField(max_length=30, default='unverified')


class ScreeningRun(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='screenings')
    provider = models.CharField(max_length=60, default='local-rules')
    model_version = models.CharField(max_length=60, default='rules-v1')
    prompt_version = models.CharField(max_length=60, default='none-local-rules')
    policy_snapshot = models.JSONField(default=dict)
    source_ids = models.JSONField(default=list)
    score = models.PositiveIntegerField(null=True)
    recommendation = models.CharField(max_length=30, default='Review Required')
    evidence = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    input_hash = models.CharField(max_length=64)


class BackgroundTask(Record):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    leased_until = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'available_at'])]


class Interview(Record):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=[('invited', 'Invited'), ('scheduled', 'Scheduled'), ('in_progress', 'In progress'), ('completed', 'Completed'), ('reviewed', 'Human reviewed')], default='invited')
    expires_at = models.DateTimeField()
    consented_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    template_version = models.CharField(max_length=60, default='recruiter-text-v1')
    rubric = models.TextField(max_length=5000)


class InterviewSlot(Record):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    interview = models.OneToOneField(Interview, null=True, blank=True, on_delete=models.SET_NULL, related_name='slot')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['company', 'starts_at'], name='unique_company_interview_slot')]


class InterviewQuestion(Record):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=1000)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']


class InterviewAnswer(Record):
    question = models.OneToOneField(InterviewQuestion, on_delete=models.CASCADE, related_name='answer')
    text = models.TextField(max_length=10000)
    updated_at = models.DateTimeField(auto_now=True)


class InterviewAssessment(Record):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='assessments')
    reviewer = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    provider = models.CharField(max_length=60, default='human')
    model_version = models.CharField(max_length=60, default='human-rubric-v1')
    score = models.PositiveIntegerField()
    explanation = models.TextField(max_length=10000)
    evidence = models.JSONField(default=list)
    rubric_snapshot = models.TextField()


class Price(Record):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, choices=[('QAR', 'QAR'), ('USD', 'USD')], default='QAR')
    active = models.BooleanField(default=True)

    @property
    def amount(self):
        from decimal import Decimal
        return Decimal(self.amount_minor) / 100


class Payment(Record):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    job = models.ForeignKey(Job, on_delete=models.PROTECT)
    price = models.ForeignKey(Price, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    item_description = models.CharField(max_length=200)
    provider = models.CharField(max_length=40, default='internal-sandbox')
    provider_reference = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=30, default='pending')
    sandbox = models.BooleanField(default=True)


class PaymentEvent(Record):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    event_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30)
    payload_hash = models.CharField(max_length=64)


class Entitlement(Record):
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT)
    job = models.ForeignKey(Job, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    sandbox = models.BooleanField(default=True)


class Invoice(Record):
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, unique=True)
    legal_snapshot = models.JSONField(default=dict)


class TeamInvitation(Record):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField()
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True)
