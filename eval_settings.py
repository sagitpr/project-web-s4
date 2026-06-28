import os, json

# Ensure env vars from .env are available via docker --env-file
settings_path = 'django_backend/config/settings.py'
ns = {}
ns['__file__'] = settings_path
ns['__name__'] = 'config.settings'
with open(settings_path, 'r', encoding='utf-8') as f:
    code = f.read()
# Execute settings.py in isolated namespace
exec(compile(code, settings_path, 'exec'), ns)

print('USE_MYSQL=', ns.get('USE_MYSQL'))
print(json.dumps(ns.get('DATABASES'), indent=2))
