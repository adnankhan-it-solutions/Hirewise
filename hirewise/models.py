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
