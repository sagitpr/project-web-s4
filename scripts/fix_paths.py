"""Fix all broken asset/JS/CSS paths across HTML files for Django static serving."""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files to fix: (relative_path, is_django_template)
FILES = [
    # Django template
    ("django_backend/templates/home/index.html", True),
    # Standalone HTML files - auth
    ("auth/login/index.html", False),
    ("auth/register/index.html", False),
    ("auth/otp/index.html", False),
    ("auth/reset-password/index.html", False),
    ("auth/register-mitra/index.html", False),
    ("auth/callback/Apple.sosial/apple.html", False),
    # Standalone HTML files - buyer
    ("buyer/dashboard/index.html", False),
    ("buyer/orders/index.html", False),
    ("buyer/cart/index.html", False),
    ("buyer/checkout/index.html", False),
    ("buyer/order-detail/index.html", False),
    ("buyer/order-success/index.html", False),
    ("buyer/profile/index.html", False),
    # Standalone HTML files - seller
    ("seller/dashboard/index.html", False),
    ("seller/products/index.html", False),
    ("seller/partner-guide/index.html", False),
    ("seller/orders/index.html", False),
    ("seller/order-detail/index.html", False),
    # Other standalone
    ("home/index.html", False),
    ("Daftar_mitra/index.html", False),
    ("panduan_mitra/index.html", False),
]

def fix_content(content, is_django_template):
    """Fix all broken paths in HTML content."""
    
    if is_django_template:
        # Django templates use {% static %}
        # ../src/assets/images/ → {% static 'images/
        regex_prefix = r'(src|href)=["\']\.\./src/assets/images/'
        def replace_static(m):
            attr = m.group(1)
            return f'{attr}={{"% static \'images/'
        
        content = re.sub(regex_prefix, replace_static, content)
        
        # Fix trailing ' %} for images in src="..." or href="..." 
        # After replacing prefix, we need to replace the closing part
        # Find {% static 'images/... " and replace the quote before the " 
        content = re.sub(
            r"({% static 'images/[^'\"}]+)['\"]\s*",
            lambda m: m.group(1) + "' %} ",
            content
        )
        
        # Fix script src paths
        # ../shared/scripts/device-detector.js → {% static 'js/device-detector.js' %}
        content = re.sub(
            r'src=["\']\.\./shared/scripts/device-detector\.js["\']',
            "src=\"{% static 'js/device-detector.js' %}\"",
            content
        )
        # ../src/utils/auth.js → {% static 'js/auth.js' %}
        content = re.sub(
            r'src=["\']\.\./src/utils/auth\.js["\']',
            "src=\"{% static 'js/auth.js' %}\"",
            content
        )
        # ../src/services/api.js → {% static 'js/api.js' %}
        content = re.sub(
            r'src=["\']\.\./src/services/api\.js["\']',
            "src=\"{% static 'js/api.js' %}\"",
            content
        )
        
        # Fix responsive.css
        content = re.sub(
            r'href=["\']\.\./shared/styles/responsive\.css["\']',
            "href=\"{% static 'css/responsive.css' %}\"",
            content
        )
        
        # Fix favicons - /assets/ → {% static '
        content = re.sub(
            r'href=["\']/assets/(favicon[^"\']+)["\']',
            lambda m: "href=\"{% static '" + m.group(1) + "' %}\"",
            content
        )
        
    else:
        # Standalone HTML - use /static/ paths
        # ../../src/assets/images/ → /static/images/
        content = re.sub(
            r'(src|href)=["\']\.\./\.\./src/assets/images/',
            lambda m: f'{m.group(1)}="/static/images/',
            content
        )
        # ../src/assets/images/ → /static/images/
        content = re.sub(
            r'(src|href)=["\']\.\./src/assets/images/',
            lambda m: f'{m.group(1)}="/static/images/',
            content
        )
        # src/assets/images/ → /static/images/
        content = re.sub(
            r'(src|href)=["\']src/assets/images/',
            lambda m: f'{m.group(1)}="/static/images/',
            content
        )
        
        # ../../src/assets/videos/ → /assets/video/
        content = re.sub(
            r'src=["\']\.\./\.\./src/assets/videos/',
            'src="/assets/video/',
            content
        )
        
        # Fix JS paths
        # ../../shared/scripts/device-detector.js → /static/js/device-detector.js
        content = re.sub(
            r'src=["\']\.\./\.\./shared/scripts/device-detector\.js["\']',
            'src="/static/js/device-detector.js"',
            content
        )
        # ../../src/utils/auth.js → /static/js/auth.js
        content = re.sub(
            r'src=["\']\.\./\.\./src/utils/auth\.js["\']',
            'src="/static/js/auth.js"',
            content
        )
        # ../../src/services/api.js → /static/js/api.js
        content = re.sub(
            r'src=["\']\.\./\.\./src/services/api\.js["\']',
            'src="/static/js/api.js"',
            content
        )
        
        # Fix shared/styles/responsive.css → /static/css/responsive.css
        content = re.sub(
            r'href=["\']\.\./\.\./shared/styles/responsive\.css["\']',
            'href="/static/css/responsive.css"',
            content
        )
        
        # Fix ../shared/styles/responsive.css → /static/css/responsive.css
        content = re.sub(
            r'href=["\']\.\./shared/styles/responsive\.css["\']',
            'href="/static/css/responsive.css"',
            content
        )
        
        # Fix ../shared/scripts/ → /static/js/
        content = re.sub(
            r'src=["\']\.\./shared/scripts/device-detector\.js["\']',
            'src="/static/js/device-detector.js"',
            content
        )
        content = re.sub(
            r'src=["\']\.\./src/utils/auth\.js["\']',
            'src="/static/js/auth.js"',
            content
        )
        content = re.sub(
            r'src=["\']\.\./src/services/api\.js["\']',
            'src="/static/js/api.js"',
            content
        )
    
    return content


def main():
    for rel_path, is_django_template in FILES:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"[SKIP] (not found): {rel_path}")
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            original = f.read()
        
        fixed = fix_content(original, is_django_template)
        
        if fixed != original:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(fixed)
            
            # Count changes
            changes = 0
            for old, new in [
                ("../../src/assets/images/", "/static/images/"),
                ("../src/assets/images/", "/static/images/"),
                ("../../shared/scripts/", "/static/js/"),
                ("../../src/services/", "/static/js/"),
                ("../../src/utils/", "/static/js/"),
                ("{% static '", "{% static '"),
            ]:
                if old in fixed:
                    changes += 1
            print(f"[FIXED]: {rel_path}")
        else:
            print(f"[OK] No changes: {rel_path}")
    
    print("\n[DONE] All paths fixed.")


if __name__ == '__main__':
    main()
