from datetime import timedelta
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from hirewise.models import Notification


class Command(BaseCommand):
    help = 'Deliver a bounded batch of durable email notifications; schedule every minute.'

    def handle(self, *args, **options):
        delivered = 0
        for pk in Notification.objects.filter(sent_at=None, attempts__lt=8, available_at__lte=timezone.now()).values_list('pk', flat=True)[:100]:
            with transaction.atomic():
                item = Notification.objects.select_for_update().get(pk=pk)
                if item.sent_at or item.available_at > timezone.now():
                    continue
                item.attempts += 1
                try:
                    send_mail(item.subject, item.body, None, [item.recipient], fail_silently=False)
                    item.sent_at = timezone.now()
                    # Token-bearing email contents need not persist after delivery.
                    item.body = ''
                    delivered += 1
                except Exception:
                    item.available_at = timezone.now() + timedelta(minutes=min(2 ** item.attempts, 120))
                item.save()
        self.stdout.write(f'Delivered {delivered} notifications.')
