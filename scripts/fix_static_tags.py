import os
import re

def fix_html(file_path):
    print(f"Fixing: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ensure load static
    if '{% load static %}' not in content:
        content = '{% load static %}\n' + content
    
    # Replace relative paths with static tags
    # assets/images/... -> {% static 'images/...' %}
    content = re.sub(r'(src|href|srcset)=["\'](?:\.\./|\./|assets/)?images/([^"\']+)["\']', r'\1="{% static \'images/\2\' %}"', content)
    
    # assets/favicon... -> {% static 'favicon...' %}
    content = re.sub(r'(src|href)=["\'](?:\.\./|\./|assets/)?favicon([^"\']+)["\']', r'\1="{% static \'favicon\2\' %}"', content)

    # staticfiles/css/... -> {% static 'css/...' %}
    content = re.sub(r'href=["\'](?:\.\./|\./)?staticfiles/css/([^"\']+)["\']', r'href="{% static \'css/\1\' %}"', content)
    
    # staticfiles/js/... -> {% static 'js/...' %}
    content = re.sub(r'src=["\'](?:\.\./|\./)?staticfiles/js/([^"\']+)["\']', r'src="{% static \'js/\1\' %}"', content)
    
    # Special case for buyer/dashboard/style.css -> {% static 'css/pages/buyer/dashboard/style.css' %}
    # If the file is buyer/dashboard/index.html, style.css usually means local
    if "buyer/dashboard" in file_path:
        content = content.replace('href="style.css"', 'href="{% static \'css/pages/buyer/dashboard/style.css\' %}"')
        content = content.replace('src="script.js"', 'src="{% static \'js/pages/buyer/dashboard/script.js\' %}"')
    elif "home" in file_path:
        content = content.replace('href="style.css"', 'href="{% static \'css/style.css\' %}"')
        content = content.replace('src="script.js"', 'src="{% static \'js/script.js\' %}"')
    elif "auth/login" in file_path:
        content = content.replace('href="style.css"', 'href="{% static \'css/pages/auth/login/style.css\' %}"')
        content = content.replace('src="script.js"', 'src="{% static \'js/pages/auth/login/script.js\' %}"')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

template_dir = 'django_backend/templates'
for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html') and not file.endswith('.bak'):
            fix_html(os.path.join(root, file))
