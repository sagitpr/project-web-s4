import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Read raw bytes of the template file
filepath = 'templates/auth/login/index.html'
with open(filepath, 'rb') as f:
    raw = f.read()

print('File size:', len(raw), 'bytes')
print('First 50 bytes (hex):', raw[:50].hex())
print('First 50 bytes (repr):', repr(raw[:50]))
print()

# Check for BOM
if raw.startswith(b'\xef\xbb\xbf'):
    print('BOM: UTF-8 BOM detected at start!')
elif raw.startswith(b'\xff\xfe'):
    print('BOM: UTF-16 LE BOM detected!')
elif raw.startswith(b'\xfe\xff'):
    print('BOM: UTF-16 BE BOM detected!')
else:
    print('BOM: None detected')
print()

# Find the load static tag
idx = raw.find(b'load static')
if idx >= 0:
    start = max(0, idx-10)
    end = min(len(raw), idx+30)
    print('load static found at byte position', idx)
    print('Context:', repr(raw[start:end]))
else:
    print('ERROR: load static NOT FOUND in raw bytes!')
    idx2 = raw.find(b'{%')
    print('First {{ at byte', idx2)
    if idx2 >= 0:
        start = max(0, idx2-5)
        end = min(len(raw), idx2+80)
        print('Context:', repr(raw[start:end]))
    
    # Also check if it's encoded differently
    idx3 = raw.find(b'load')
    if idx3 >= 0:
        print('First \"load\" at byte', idx3)
        start = max(0, idx3-10)
        end = min(len(raw), idx3+30)
        print('Context:', repr(raw[start:end]))
        print('Is it inside {{ tag?')
        # Check if there's {{ before this
        before = raw[max(0, idx3-20):idx3]
        print('  bytes before:', repr(before))
        if b'{%' in before:
            print('  YES - but the full tag might be malformed')
        else:
            print('  NO - it is not inside a template tag')

# Also find the first template tag
print()
print('Searching for {%% tags...')
count = 0
pos = 0
while count < 5:
    pos = raw.find(b'{%', pos)
    if pos < 0:
        break
    end_pos = raw.find(b'%}', pos)
    if end_pos < 0:
        tag_content = raw[pos:pos+50]
        print('  Found {{ at', pos, 'but no closing %} - content:', repr(tag_content))
    else:
        tag_content = raw[pos:end_pos+2]
        print('  Found:', repr(tag_content))
    pos = end_pos + 2 if end_pos > 0 else pos + 2
    count += 1

# Check the rendered output
print()
print('=== RENDERED OUTPUT ===')
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist

try:
    html = render_to_string('auth/login/index.html', {}, using='django')
    head_start = html.find('<head>')
    head_end = html.find('</head>')
    if head_start >= 0 and head_end >= 0:
        print(html[head_start:head_end+7])
    else:
        print(html[:500])
except Exception as e:
    print('ERROR:', e)
