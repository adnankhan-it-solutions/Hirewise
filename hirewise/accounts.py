from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import Notification
from .security import throttle


class QueuedPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        origin = urlsplit(settings.PUBLIC_ORIGIN)
        context['domain'] = origin.netloc
        context['protocol'] = origin.scheme
        subject = ''.join(render_to_string(subject_template_name, context).splitlines())
        Notification.objects.create(user=context['user'], recipient=to_email, subject=subject,
                                    body=render_to_string(email_template_name, context))


class QueuedPasswordResetView(PasswordResetView):
    form_class = QueuedPasswordResetForm
    template_name = 'registration/password_reset_form.html'

    def post(self, request, *args, **kwargs):
        if throttle(f'password-reset:{request.META.get("REMOTE_ADDR")}', 5, 3600):
            return HttpResponse('Please try again later.', status=429)
        return super().post(request, *args, **kwargs)
