import os
import json
import importlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    settings = importlib.import_module('config.settings')
    print('USE_MYSQL=', settings.USE_MYSQL)
    print(json.dumps(settings.DATABASES, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
