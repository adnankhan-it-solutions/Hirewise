"""Export a public, data-free project site for GitHub Pages."""
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings


class Command(BaseCommand):
    help = 'Build a static project/launch site. Never exports database records or private workflows.'

    def add_arguments(self, parser):
        parser.add_argument('--base-path', default='/Hirewise/')
        parser.add_argument('--output', default='public-site')

    def handle(self, *args, **options):
        base = options['base_path']
        if not re.fullmatch(r'/[A-Za-z0-9_/-]*/?', base):
            raise CommandError('Base path must be a safe URL path.')
        base = base.rstrip('/') + '/'
        output = Path(options['output']).resolve()
        if output == settings.BASE_DIR or settings.BASE_DIR not in output.parents:
            raise CommandError('Output must be a subdirectory of the repository.')
        output.mkdir(parents=True, exist_ok=True)
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        request.pages_export = True
        pages = {
            '': ('home.html', {}),
            'jobs': ('info.html', {'title': 'Opportunities are on the way.', 'body': 'Hirewise is preparing to launch. Live vacancies and applications are not open yet. This public project site does not collect CVs, create accounts, or process payments.'}),
            'status': ('info.html', {'title': 'A thoughtful platform, taking shape.', 'body': 'Hirewise is in development. Our source repository contains the recruitment application, while this GitHub Pages site introduces the project. Secure account services, private CV storage, email delivery, approved AI processing and merchant services require backend hosting and verification before launch. No real applications are being accepted here.'}),
            'pages/about': ('info.html', {'title': 'A clearer view of potential.', 'body': 'Hirewise is a recruitment platform being built for Qatar. Our aim is to help candidates present relevant experience and help employers make more considered decisions, supported by clear evidence and human oversight.'}),
            'pages/how-it-works': ('info.html', {'title': 'Built around a more human journey.', 'body': 'The planned service brings published vacancies, private applications, evidence-based screening and recruiter-reviewed interviews together. Candidates share information for a particular role. Recruiters see supporting evidence, understand unknowns, and remain responsible for decisions. The full service is not yet open.'}),
            'pages/employers': ('info.html', {'title': 'Good teams start with understanding.', 'body': 'Hirewise is being developed to give hiring teams private company workspaces, structured vacancies, application histories and evidence-led reviews. Employer registration and paid services will become available after backend hosting and launch verification are complete.'}),
            'pages/candidates': ('info.html', {'title': 'Your potential deserves a fair view.', 'body': 'Our planned candidate experience includes applications with or without an account, private CV handling, a clear application reference and control over personal information. Applications are not open on this project site. Please do not send CVs through GitHub issues or public repository discussions.'}),
            'pages/privacy': ('info.html', {'title': 'Privacy on this project site.', 'body': 'This static site does not accept applications, create accounts, collect CVs, install advertising trackers or process payments. GitHub Pages hosts the site and may log visitor IP addresses for security; see GitHub’s Privacy Statement. The recruitment service’s controller identity, processing notices, retention policies and provider details will be published after professional review and before real candidate intake.'}),
            'pages/cookies': ('info.html', {'title': 'No application cookies here.', 'body': 'This public project site does not set application session cookies or use analytics or advertising scripts. GitHub provides the hosting infrastructure. A future authenticated recruitment service will use essential security and session cookies and disclose them before launch.'}),
            'pages/terms': ('info.html', {'title': 'About this preview.', 'body': 'This website introduces a project in development. It is not an offer of live recruitment or payment services, and it does not guarantee job opportunities or employment outcomes. Final service terms and legal entity information will be published before the service opens.'}),
            'pages/security': ('info.html', {'title': 'Security starts before the first application.', 'body': 'The application under development includes server-side company permissions, administrator MFA, private document quarantine and audit histories. This static site contains no candidate records. Production infrastructure, independent security review and recovery verification remain launch requirements. No security certification is claimed.'}),
            'pages/contact': ('info.html', {'title': 'Stay connected.', 'body': 'The public support address has not been configured yet. Project development is tracked in the Hirewise source repository. Do not submit personal application information to public GitHub issues.'}),
        }
        with override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}):
            for route, (template, context) in pages.items():
                context.update(platform_name=settings.PLATFORM_NAME, development=False, pages_mode=True, support_email='', user=request.user)
                html = render_to_string(template, context, request=request)
                html = re.sub(r'<form class="job-search".*?</form>', '<a class="button" href="/jobs/">Explore what’s next ↗</a>', html, flags=re.S)
                html = re.sub(r'href="/accounts/[^\"]*"', 'href="/status/"', html)
                html = html.replace('Get started', 'Launch status').replace('Sign in</a>', 'Platform status</a>').replace('Start hiring ↗', 'Explore the platform ↗')
                html = re.sub(r'(href|src|action)="/(?!/)', lambda match: match[1] + '="' + base, html)
                html = html.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\' data:; style-src \'self\'; base-uri \'self\'; form-action \'none\'">')
                html = html.replace('</head>', f'<link rel="canonical" href="https://adnankhan-it-solutions.github.io{base}{route + "/" if route else ""}"></head>')
                folder = output / route
                folder.mkdir(parents=True, exist_ok=True)
                (folder / 'index.html').write_text(html)
        shutil.copytree(settings.BASE_DIR / 'static', output / 'static', dirs_exist_ok=True)
        (output / '.nojekyll').write_text('')
        (output / '404.html').write_text((output / 'status/index.html').read_text())
        (output / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: https://adnankhan-it-solutions.github.io{base}sitemap.xml\n')
        urls = ''.join(f'<url><loc>https://adnankhan-it-solutions.github.io{base}{route + "/" if route else ""}</loc></url>' for route in pages)
        (output / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
        self.stdout.write(f'Built {len(pages)} public pages in {output}. No database data exported.')
