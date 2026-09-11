import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'
SECRET_KEY = os.environ.get('SECRET_KEY', 'local-development-only-change-before-deployment-39394')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if x]
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'hirewise',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hirewise.middleware.SecurityMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages', 'hirewise.context.brand',
              ]}}]
DATABASES = {'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=60)}
AUTH_USER_MODEL = 'hirewise.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher', 'django.contrib.auth.hashers.PBKDF2PasswordHasher']
LANGUAGE_CODE = 'en'
LANGUAGES = [('en', 'English'), ('ar', 'Arabic')]
TIME_ZONE = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Qatar')
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': BASE_DIR / 'private-media'}},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
# Enable only behind a proxy that strips incoming X-Forwarded-Proto.
if os.environ.get('TRUST_PROXY') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Hirewise <noreply@example.invalid>')
PUBLIC_ORIGIN = os.environ.get('PUBLIC_ORIGIN', 'http://localhost:8000').rstrip('/')
PLATFORM_NAME = os.environ.get('PLATFORM_NAME', 'Hirewise')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', '')
MFA_ENCRYPTION_KEY = os.environ.get('MFA_ENCRYPTION_KEY', '')
UPLOAD_MAX_BYTES = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
PASSWORD_RESET_TIMEOUT = 3600
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}, 'null': {'class': 'logging.NullHandler'}},
           'root': {'handlers': ['console'], 'level': 'WARNING'},
           'loggers': {'hirewise.requests': {'handlers': ['console'], 'level': 'INFO' if not DEBUG else 'WARNING', 'propagate': False},
                       # Raw request URLs may contain one-time verification/download tokens.
                       'django.server': {'handlers': ['null'], 'propagate': False},
                       'django.request': {'handlers': ['null'], 'propagate': False},
                       'django.security': {'handlers': ['null'], 'propagate': False}}}
if not DEBUG:
    if SECRET_KEY.startswith('local-') or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured('Production requires a random SECRET_KEY of at least 50 characters.')
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Production requires PostgreSQL.')
    if not MFA_ENCRYPTION_KEY or not PUBLIC_ORIGIN.startswith('https://'):
        raise ImproperlyConfigured('Production requires MFA_ENCRYPTION_KEY and HTTPS PUBLIC_ORIGIN.')
    if EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
        raise ImproperlyConfigured('Production requires configured transactional SMTP.')
