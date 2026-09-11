from getpass import getpass
import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from hirewise.models import User


class Command(BaseCommand):
    help = 'Create a verified administrator interactively; MFA enrollment is mandatory at first login.'

    def add_arguments(self, parser):
        parser.add_argument('email')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError('Email already exists; existing accounts are never silently promoted.')
        password = getpass('New administrator password: ')
        if password != getpass('Repeat password: '):
            raise CommandError('Passwords do not match.')
        user = User(username=str(uuid.uuid4()), email=email, role='admin', email_verified=True)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS('Administrator created. Enroll your authenticator at first login.'))
