import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("ALTER TABLE django_content_type ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT '';")
print("Successfully added name column to django_content_type.")
