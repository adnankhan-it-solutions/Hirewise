import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from hirewise.models import Application, CandidateProfile, Company, Job, Membership, Price, Requirement, StatusEvent, User


class Command(BaseCommand):
    help = 'Create synthetic local demo accounts, companies and vacancies with random passwords.'

    def handle(self, *args, **options):
        if settings.ENVIRONMENT != 'development':
            raise CommandError('Demo data is forbidden outside development.')
        if User.objects.filter(email__endswith='@demo.example.invalid').exists():
            raise CommandError('Demo data already exists. Existing passwords are not reset.')
        credentials = []
        with transaction.atomic():
            users = {}
            for name, role in [('admin', 'admin'), ('recruiter-a', 'recruiter'), ('recruiter-b', 'recruiter'), ('candidate', 'candidate')]:
                password = secrets.token_urlsafe(18)
                email = f'{name}@demo.example.invalid'
                user = User.objects.create_user(username=email, email=email, password=password, first_name=name.title(), role=role, email_verified=True)
                users[name] = user
                credentials.append((email, password))
            CandidateProfile.objects.create(user=users['candidate'], headline='Synthetic software professional', location='Doha')
            for suffix in ['a', 'b']:
                company = Company.objects.create(name=f'Demo Company {suffix.upper()}', status='approved', description='Fictional company used only for local demonstrations.')
                Membership.objects.create(user=users[f'recruiter-{suffix}'], company=company, role='owner')
                for title, department in [('Software Engineer', 'Engineering'), ('Operations Specialist', 'Operations'), ('Product Designer', 'Design')]:
                    job = Job.objects.create(company=company, created_by=users[f'recruiter-{suffix}'], title=title, department=department,
                                             description='Synthetic vacancy. Work with a thoughtful team to build reliable products and deliver a better customer experience. This is not a real job advertisement.',
                                             responsibilities='Collaborate across the team. Document decisions. Deliver work with care.', requirements_text='Relevant experience and clear examples of your work.',
                                             status='published', published_at=timezone.now(), interview_enabled=True, workplace='hybrid')
                    if title == 'Software Engineer':
                        Requirement.objects.create(job=job, label='Python', category='skill', weight=25)
                        Requirement.objects.create(job=job, label='PostgreSQL', category='skill', weight=20)
                    if suffix == 'a' and title == 'Software Engineer':
                        item = Application.objects.create(job=job, candidate=users['candidate'], name='Synthetic Candidate', email=users['candidate'].email, email_verified=True,
                                                          cover_letter='Fictional application for local testing.', expires_at=timezone.now() + timedelta(days=180))
                        StatusEvent.objects.create(application=item, actor=users['candidate'], current='received', reason='Synthetic seed application')
            Price.objects.create(name='Development job package', description='Internal sandbox package; no funds collected.', amount_minor=10000)
        self.stdout.write('Synthetic local credentials (save privately; never use for production):')
        for email, password in credentials:
            self.stdout.write(f'{email}  {password}')
        self.stdout.write('Administrator still requires authenticator enrollment.')
