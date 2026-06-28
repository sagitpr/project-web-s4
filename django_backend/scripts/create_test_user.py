import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from django.contrib.auth import authenticate

email = 'test@warungio.local'
password = 'Test123456!'
username = 'test'
full_name = 'Test User'

if User.objects.filter(email=email).exists():
    u = User.objects.get(email=email)
    u.set_password(password)
    u.is_active = True
    u.is_verified = True
    u.role = 'buyer'
    u.save()
    print('EXISTS_AND_UPDATED', u.id)
else:
    u = User.objects.create_user(username=username, email=email, password=password, full_name=full_name, is_verified=True)
    u.role = 'buyer'
    u.save()
    print('CREATED', u.id)

# Verify password hash exists
has_hash = bool(getattr(u, 'password', None))
print('PASSWORD_HASH_PRESENT', has_hash)

# Verify authenticate()
user = authenticate(email=email, password=password)
print('AUTHENTICATE_SUCCESS', bool(user))
print('USER_ID', u.id)
