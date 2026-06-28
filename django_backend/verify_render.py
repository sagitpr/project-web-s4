import os, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.template.loader import render_to_string

html = render_to_string('auth/login/index.html', {}, using='django')
print('=== CSS links ===')
css = re.findall(r'<link[^>]*stylesheet[^>]*>', html)
for c in css:
    print(' ', c)

print()
print('=== JS src ===')
js = re.findall(r'<script[^>]*src="([^"]*)"', html)
for s in js:
    if 'static' in s or s.startswith('/static/'):
        print(' ', s)

print()
print('=== Image src ===')
imgs = re.findall(r'<img[^>]*src="([^"]*)"', html)
for i in imgs[:5]:
    if 'static' in i or i.startswith('/static/'):
        print(' ', i)
if len(imgs) > 5:
    print(f'  ... ({len(imgs)-5} more)')

print()
print('Total CSS links:', len(css))
print('Total JS scripts:', len(js))
print('Total images:', len(imgs))

# Check for any template syntax errors
if '%}' in html:
    print()
    print('WARNING: found %} artifacts in rendered HTML!')
    for i, line in enumerate(html.split('\n')):
        if '%}' in line:
            print(f'  Line {i+1}: {line.strip()[:100]}')
else:
    print()
    print('No template syntax artifacts found - rendering is clean!')
