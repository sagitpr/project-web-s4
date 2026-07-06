#!/usr/bin/env python3
"""Debug P0.3 - detection_results table error."""
import os
os.environ['DJANGO_ALLOWED_HOSTS'] = '*'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

import traceback
from accounts.models import User
from django.db import connection

# Check for detection_results table
with connection.cursor() as c:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%detect%' OR name LIKE '%ocr%'")
    tables = [r[0] for r in c.fetchall()]
    print("Detection/OCR tables:", tables)

# Try creating, then deleting a user
u = User.objects.create_user(
    email='debug_delete@test.com',
    password='Test@123456',
    full_name='Debug Delete',
    phone='08123450000',
)
print(f"Created user ID={u.id}")

try:
    User.objects.filter(email='debug_delete@test.com').delete()
    print("Delete SUCCESS")
except Exception:
    print("Delete FAILED:")
    traceback.print_exc()

u2 = User.objects.create_user(
    email='debug_delete2@test.com',
    password='Test@123456',
    full_name='Debug Delete 2',
    phone='08123450001',
)
print(f"Created user2 ID={u2.id}")

try:
    u2.delete()
    print("Instance delete SUCCESS")
except Exception:
    print("Instance delete FAILED:")
    traceback.print_exc()
