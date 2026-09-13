"""Real-browser local smoke test. Uses synthetic data only, never an external site."""
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Playwright's synchronous facade runs an event loop internally. This standalone,
# single-process test performs no concurrent ORM work.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
import django

django.setup()
from django.conf import settings
from hirewise.models import Application, Company, Job, Membership, User
from playwright.sync_api import sync_playwright

if settings.ENVIRONMENT != 'development':
    raise RuntimeError('Browser smoke test is only allowed against a local development environment.')

password = secrets.token_urlsafe(22)
suffix = secrets.token_hex(6)
recruiter = User.objects.create_user(username=f'recruiter-{suffix}', email=f'recruiter-{suffix}@example.invalid', password=password, role='recruiter', email_verified=True)
candidate = User.objects.create_user(username=f'candidate-{suffix}', email=f'candidate-{suffix}@example.invalid', password=password, role='candidate', email_verified=True)
company = Company.objects.create(name=f'Synthetic Browser Company {suffix}', status='approved')
Membership.objects.create(user=recruiter, company=company, role='owner')
job = Job.objects.create(company=company, created_by=recruiter, title=f'Synthetic Engineer {suffix}', description='Fictional browser-test vacancy. No real opportunity.', status='published')
artifacts = settings.BASE_DIR / 'test-results'
artifacts.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    for route in ['/', '/jobs/', '/accounts/register/', '/accounts/login/', '/pricing/', '/pages/privacy/']:
        response = page.goto('http://127.0.0.1:8000' + route)
        assert response.status == 200, (route, response.status)
        assert page.locator('h1').count() == 1, route
    page.goto('http://127.0.0.1:8000/')
    page.screenshot(path=str(artifacts / 'home-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(artifacts / 'home-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
    page.goto('http://127.0.0.1:8000/accounts/login/')
    page.locator('[name=username]').fill(candidate.email)
    page.locator('[name=password]').fill(password)
    page.get_by_role('button', name='Sign in', exact=False).click()
    page.wait_for_url('**/dashboard/')
    page.goto(f'http://127.0.0.1:8000/jobs/{job.pk}/apply/')
    page.locator('[name=name]').fill('Synthetic Browser Candidate')
    page.locator('[name=cv]').set_input_files({'name': 'synthetic-cv.txt', 'mimeType': 'text/plain', 'buffer': b'Synthetic CV. Python and PostgreSQL.'})
    page.locator('[name=processing_consent]').check()
    page.get_by_role('button', name='Submit application').click()
    page.wait_for_url('**/applications/received/')
    assert 'Your application is received' in page.locator('h1').inner_text()
    application = Application.objects.get(candidate=candidate, job=job)
    page.get_by_role('button', name='Sign out').click()
    page.goto('http://127.0.0.1:8000/accounts/login/')
    page.locator('[name=username]').fill(recruiter.email)
    page.locator('[name=password]').fill(password)
    page.get_by_role('button', name='Sign in', exact=False).click()
    page.wait_for_url('**/dashboard/')
    page.goto(f'http://127.0.0.1:8000/applications/{application.pk}/')
    assert 'Candidate review' in page.locator('h1').inner_text()
    assert 'quarantined' in page.locator('body').inner_text()
    page.locator('[name=stage]').select_option('shortlisted')
    page.locator('[name=reason]').fill('Synthetic human review for browser test.')
    page.get_by_role('button', name='Record decision').click()
    page.wait_for_load_state()
    application.refresh_from_db()
    assert application.stage == 'shortlisted'
    assert application.history.count() == 2
    assert not errors, errors
    browser.close()

print('Desktop/mobile, candidate login/upload/confirmation and recruiter human decision browser checks passed. Synthetic data retained locally.')
