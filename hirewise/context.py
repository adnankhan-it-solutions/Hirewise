from django.conf import settings


def brand(request):
    return {'platform_name': settings.PLATFORM_NAME, 'support_email': settings.SUPPORT_EMAIL,
            'development': settings.DEBUG}
