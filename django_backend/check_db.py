import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
print("User count:", User.objects.count())
print("User fields:", [f.name for f in User._meta.fields])
