import io
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from hirewise.models import Application, Company, Job, Notification, User
from hirewise.privacy import anonymize_application


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PrivacySiteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='privacy-user', email='privacy@example.test', password='SafePassword!88839', email_verified=True)
        company = Company.objects.create(name='Example')
        job = Job.objects.create(company=company, created_by=self.user, title='Synthetic role', description='Synthetic')
        self.item = Application.objects.create(job=job, candidate=self.user, name='Personal name', email=self.user.email, email_verified=True,
                                               cover_letter='Private candidate text', expires_at=timezone.now() - timedelta(days=1), stage='rejected')

    def test_retention_preview_does_not_delete_and_execute_scrubs(self):
        call_command('enforce_retention', stdout=io.StringIO())
        self.item.refresh_from_db()
        self.assertIsNone(self.item.anonymized_at)
        call_command('enforce_retention', execute=True, stdout=io.StringIO())
        self.item.refresh_from_db()
        self.assertEqual(self.item.cover_letter, '')
        self.assertIsNone(self.item.candidate_id)
        self.assertIsNotNone(self.item.anonymized_at)

    def test_legal_hold_blocks_anonymization(self):
        self.item.legal_hold = True
        self.item.save()
        with self.assertRaises(ValueError):
            anonymize_application(self.item.pk, 'test')
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Personal name')

    def test_password_reset_is_queued_with_trusted_origin(self):
        response = self.client.post('/accounts/password-reset/', {'email': self.user.email})
        self.assertEqual(response.status_code, 302)
        item = Notification.objects.get(user=self.user)
        self.assertIn(settings.PUBLIC_ORIGIN, item.body)
        self.assertNotIn('testserver', item.body)

    def test_public_site_export_has_no_database_data_or_account_forms(self):
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as output:
            with self.assertNumQueries(0):
                call_command('build_public_site', output=output, stdout=io.StringIO())
            index = (Path(output) / 'index.html').read_text()
            self.assertIn('/Hirewise/static/style.css', index)
            self.assertNotIn('<form', index)
            self.assertNotIn('/accounts/', index)
            self.assertNotIn('Private candidate text', index)
            self.assertNotIn('Development workspace', index)
            self.assertTrue((Path(output) / 'status/index.html').exists())

    def test_demo_seed_refuses_production(self):
        from django.core.management.base import CommandError
        with override_settings(ENVIRONMENT='production'), self.assertRaises(CommandError):
            call_command('seed_demo')

    def test_logging_does_not_contain_request_token(self):
        with patch('hirewise.middleware.logging.getLogger') as logger:
            self.client.get('/documents/download/extremely-private-token/')
        message = logger.return_value.info.call_args[0][0]
        self.assertNotIn('extremely-private-token', message)
        self.assertIn('request_id', message)
