import hashlib
from datetime import timedelta

import pyotp
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from hirewise.models import AuditEvent, Company, EmailToken, Membership, User
from hirewise.security import cipher


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class FoundationTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(username='a', email='a@example.com', password='StrongPassword!3849', role='recruiter', email_verified=True)
        self.b = User.objects.create_user(username='b', email='b@example.com', password='StrongPassword!3849', role='recruiter', email_verified=True)
        self.candidate = User.objects.create_user(username='c', email='c@example.com', password='StrongPassword!3849', email_verified=True)
        self.company = Company.objects.create(name='Company A', status='approved')
        Membership.objects.create(user=self.a, company=self.company, role='owner')

    def test_company_isolation_and_membership_revocation(self):
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(f'/portal/company/{self.company.pk}/').status_code, 404)
        self.client.force_login(self.a)
        self.assertEqual(self.client.get(f'/portal/company/{self.company.pk}/').status_code, 200)
        Membership.objects.update(active=False)
        self.assertEqual(self.client.get(f'/portal/company/{self.company.pk}/').status_code, 404)

    def test_candidate_cannot_create_company_or_moderate(self):
        self.client.force_login(self.candidate)
        self.assertEqual(self.client.get('/portal/company/new/').status_code, 403)
        self.assertEqual(self.client.post(f'/portal/admin/company/{self.company.pk}/', {'status': 'approved', 'reason': 'spoof'}).status_code, 403)

    def test_recruiter_cannot_access_admin(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(f'/portal/admin/company/{self.company.pk}/', {'status': 'suspended', 'reason': 'spoof'}).status_code, 403)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, 'approved')

    def test_admin_requires_mfa_and_blocks_replayed_codes(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', role='admin', email_verified=True)
        secret = pyotp.random_base32()
        admin.mfa_enabled = True
        admin.mfa_secret = cipher().encrypt(secret.encode()).decode()
        admin.save()
        self.client.force_login(admin)
        self.assertRedirects(self.client.get('/dashboard/'), '/accounts/mfa/', fetch_redirect_response=False)
        self.assertRedirects(self.client.post('/accounts/mfa/', {'code': pyotp.TOTP(secret).now()}), '/dashboard/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)
        self.client.post('/accounts/logout/')
        self.client.force_login(admin)
        self.assertEqual(self.client.post('/accounts/mfa/', {'code': pyotp.TOTP(secret).now()}).status_code, 200)
        self.assertNotIn('mfa_user', self.client.session)

    def test_verification_is_expiring_post_only_and_single_use(self):
        raw = 'test-secret'
        token = EmailToken.objects.create(user=self.a, digest=hashlib.sha256(raw.encode()).hexdigest(), expires_at=timezone.now() + timedelta(hours=1))
        self.client.get(f'/accounts/verify/{raw}/')
        token.refresh_from_db()
        self.assertIsNone(token.used_at)
        self.assertEqual(self.client.post(f'/accounts/verify/{raw}/').status_code, 302)
        self.assertEqual(self.client.post(f'/accounts/verify/{raw}/').status_code, 400)

    def test_registration_rejects_admin_role(self):
        response = self.client.post('/accounts/register/', {'email': 'hacker@example.com', 'role': 'admin', 'password1': 'SecureLongPassword!484', 'password2': 'SecureLongPassword!484'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='hacker@example.com').exists())

    def test_csrf_and_logout_invalidate_session(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.a)
        self.assertEqual(client.post('/portal/company/new/', {'name': 'Forged'}).status_code, 403)
        self.client.force_login(self.a)
        old_cookie = self.client.cookies['sessionid'].value
        self.assertEqual(self.client.get('/accounts/logout/').status_code, 405)
        self.client.post('/accounts/logout/')
        self.client.cookies['sessionid'] = old_cookie
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)

    def test_private_headers_and_public_html(self):
        self.client.force_login(self.a)
        response = self.client.get('/dashboard/')
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.assertIn('noindex', response['X-Robots-Tag'])
        self.assertIn("frame-ancestors 'none'", response['Content-Security-Policy'])
        self.assertContains(self.client.get('/'), 'Your next chapter')

    def test_unverified_account_cannot_enter_portal(self):
        self.a.email_verified = False
        self.a.save()
        self.client.force_login(self.a)
        self.assertRedirects(self.client.get('/dashboard/'), '/accounts/verification/', fetch_redirect_response=False)

    def test_human_moderation_has_audit_record(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', role='admin', email_verified=True, mfa_enabled=True)
        self.client.force_login(admin)
        session = self.client.session
        session['mfa_user'] = str(admin.pk)
        session.save()
        self.client.post(f'/portal/admin/company/{self.company.pk}/', {'status': 'suspended', 'reason': 'Registration requires clarification'})
        self.assertTrue(AuditEvent.objects.filter(action='company.moderated', reason='Registration requires clarification').exists())
