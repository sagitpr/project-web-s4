import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# ensure project root is on path
sys.path.insert(0, os.path.abspath('.'))

try:
    django.setup()
    from django.conf import settings

    print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
    print('EMAIL_HOST:', settings.EMAIL_HOST)
    print('EMAIL_PORT:', settings.EMAIL_PORT)
    print('EMAIL_USE_TLS:', settings.EMAIL_USE_TLS)
    print('DEFAULT_FROM_EMAIL:', settings.DEFAULT_FROM_EMAIL)
    print('EMAIL_HOST_USER_CONFIGURED:', 'Yes' if getattr(settings, 'EMAIL_HOST_USER', '') else 'No')
    print('EMAIL_HOST_PASSWORD_CONFIGURED:', 'Yes' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else 'No')

    missing = []
    if 'smtp' not in settings.EMAIL_BACKEND.lower():
        missing.append('EMAIL_BACKEND not SMTP')
    if not settings.EMAIL_HOST:
        missing.append('EMAIL_HOST')
    if not settings.EMAIL_PORT:
        missing.append('EMAIL_PORT')
    if not settings.DEFAULT_FROM_EMAIL:
        missing.append('DEFAULT_FROM_EMAIL')
    if not getattr(settings, 'EMAIL_HOST_USER', ''):
        missing.append('EMAIL_HOST_USER')
    if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
        missing.append('EMAIL_HOST_PASSWORD')

    ready = not missing
    print('READY_FOR_SMTP_TESTING:', 'Yes' if ready else 'No')
    if not ready:
        print('MISSING_VALUES: ' + ', '.join(missing))

except Exception as e:
    print('ERROR_READING_SETTINGS:', e)
