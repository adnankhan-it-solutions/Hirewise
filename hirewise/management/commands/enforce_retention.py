from django.core.management.base import BaseCommand
from django.utils import timezone
from hirewise.models import Application
from hirewise.privacy import anonymize_application


class Command(BaseCommand):
    help = 'Preview or execute a bounded retention batch. Legal holds are excluded.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true')

    def handle(self, *args, **options):
        rows = Application.objects.filter(expires_at__lte=timezone.now(), legal_hold=False, anonymized_at=None, stage__in=['rejected', 'withdrawn', 'archived'])
        ids = list(rows.values_list('pk', flat=True)[:100])
        if not options['execute']:
            self.stdout.write(f'{len(ids)} applications eligible in this batch. No data changed. Use --execute only after policy review.')
            return
        count = 0
        for pk in ids:
            count += anonymize_application(pk, 'Configured retention period expired')
        self.stdout.write(f'Anonymized {count} applications. Backup expiry must follow the documented retention schedule.')
