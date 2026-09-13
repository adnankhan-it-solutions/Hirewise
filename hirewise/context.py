from django.conf import settings


def brand(request):
    name, email = settings.PLATFORM_NAME, settings.SUPPORT_EMAIL
    if not getattr(request, 'pages_export', False):
        from .models import PlatformConfig
        config = PlatformConfig.objects.filter(pk=1).first()
        if config:
            name, email = config.platform_name, config.support_email
    return {'platform_name': name, 'platform_logo': settings.PLATFORM_LOGO, 'support_email': email,
            'development': settings.ENVIRONMENT == 'development'}
