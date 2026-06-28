#!/usr/bin/env python3
"""Fix broken asset paths in Warungio static HTML/JS/CSS files."""

import os
import re
import sys

PROJECT = r"C:\Users\ThinkPad\OneDrive\Documents\GitHub\project-web-s4"

def depth(rel_path):
    """Count directory depth."""
    return len(os.path.normpath(rel_path).split(os.sep)) - 1

def fix_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    rel = os.path.relpath(filepath, PROJECT)
    d = depth(rel)
    prefix = '../' * d

    changes = 0

    # /static/images/XXX -> prefix + assets/images/XXX
    new_content = re.sub(
        r'(src=[\"\'])/static/images/',
        lambda m: m.group(1) + prefix + 'assets/images/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /assets/images/XXX -> prefix + assets/images/XXX
    new_content = re.sub(
        r'(src=[\"\'])/assets/images/',
        lambda m: m.group(1) + prefix + 'assets/images/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /assets/video/XXX -> prefix + assets/video/XXX
    new_content = re.sub(
        r'(src=[\"\'])/assets/video/',
        lambda m: m.group(1) + prefix + 'assets/video/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /assets/audio/XXX -> prefix + assets/audio/XXX
    new_content = re.sub(
        r'(src=[\"\'])/assets/audio/',
        lambda m: m.group(1) + prefix + 'assets/audio/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /assets/favicon* -> prefix + assets/favicon*
    new_content = re.sub(
        r'(href=[\"\'])/assets/(favicon[^\'\"]*)',
        lambda m: m.group(1) + prefix + 'assets/' + m.group(2),
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /static/css/responsive.css -> prefix + staticfiles/css/responsive.css
    new_content = re.sub(
        r'(href=[\"\'])/static/css/responsive\.css',
        lambda m: m.group(1) + prefix + 'staticfiles/css/responsive.css',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /static/css/pages/ -> prefix + staticfiles/css/pages/
    new_content = re.sub(
        r'(href=[\"\'])/static/css/pages/',
        lambda m: m.group(1) + prefix + 'staticfiles/css/pages/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /static/css/ (other) -> prefix + staticfiles/css/
    new_content = re.sub(
        r'(href=[\"\'])/static/css/',
        lambda m: m.group(1) + prefix + 'staticfiles/css/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    # /static/js/XXX -> prefix + staticfiles/js/XXX
    new_content = re.sub(
        r'(src=[\"\'])/static/js/',
        lambda m: m.group(1) + prefix + 'staticfiles/js/',
        content
    )
    if new_content != content:
        changes += 1
        content = new_content

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, original, content
    return False, original, content

def fix_js_strings(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # Fix '../../src/assets/images/' -> '../../assets/images/'
    content = content.replace("'../../src/assets/images/", "'../../assets/images/")
    content = content.replace('"../../src/assets/images/', '"../../assets/images/')

    # Fix 'src/assets/images/' -> '../assets/images/' (for depth=1 files like home/)
    rel = os.path.relpath(filepath, PROJECT)
    d = depth(rel)
    if d == 1:
        content = content.replace("'src/assets/images/", "'../assets/images/")
        content = content.replace('"src/assets/images/', '"../assets/images/')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Find all HTML files in specific directories
html_fixed = []
js_fixed = []

for root, dirs, files in os.walk(PROJECT):
    # Skip django_backend, staticfiles, mariadb, node_modules-like dirs
    rel_root = os.path.relpath(root, PROJECT)
    parts = rel_root.split(os.sep)
    if len(parts) > 0 and parts[0] in ('django_backend', 'staticfiles', 'mariadb-10.11.10', 'backend', '.git', '__pycache__', 'node_modules'):
        continue
    # Only process specific dirs for HTML
    if not any(parts[0] == d for d in ('auth', 'buyer', 'seller', 'home', 'reports')):
        if not any(f.endswith('.html') for f in files):
            continue
        # Only process JS in these dirs and root
        if not any(f.endswith('.js') for f in files):
            continue
        # Actually, only process our targeted dirs
        if not any(parts[0] == d for d in ('auth', 'buyer', 'seller', 'home')):
            continue

    for f in files:
        fp = os.path.join(root, f)
        if f.endswith('.html'):
            changed, old, new = fix_html(fp)
            if changed:
                html_fixed.append((rel_root + '/' + f, len(old), len(new)))
        elif f.endswith('.js'):
            changed = fix_js_strings(fp)
            if changed:
                js_fixed.append((rel_root + '/' + f))

# Also fix the django_backend/static/js files
for root, dirs, files in os.walk(os.path.join(PROJECT, 'django_backend', 'static', 'js')):
    for f in files:
        if f.endswith('.js'):
            fp = os.path.join(root, f)
            changed = fix_js_strings(fp)
            if changed:
                rel = os.path.relpath(fp, PROJECT)
                js_fixed.append(rel)

# Also fix staticfiles/js files
staticfiles_js = os.path.join(PROJECT, 'staticfiles', 'js')
if os.path.isdir(staticfiles_js):
    for root, dirs, files in os.walk(staticfiles_js):
        for f in files:
            if f.endswith('.js'):
                fp = os.path.join(root, f)
                changed = fix_js_strings(fp)
                if changed:
                    rel = os.path.relpath(fp, PROJECT)
                    js_fixed.append(rel)

# Print summary
print("=" * 60)
print("ASSET PATH FIX REPORT")
print("=" * 60)

if html_fixed:
    print(f"\nHTML files fixed: {len(html_fixed)}")
    for path, old_sz, new_sz in sorted(html_fixed):
        print(f"  {path} ({old_sz} -> {new_sz} bytes)")

if js_fixed:
    print(f"\nJS files fixed: {len(js_fixed)}")
    for path in sorted(set(js_fixed)):
        print(f"  {path}")

print(f"\nTotal: {len(html_fixed)} HTML + {len(set(js_fixed))} JS files fixed")

# Also report any remaining broken paths
print("\n" + "=" * 60)
print("REMAINING ISSUE CHECK")
print("=" * 60)
remaining = 0
for root, dirs, files in os.walk(PROJECT):
    rel_root = os.path.relpath(root, PROJECT)
    parts = rel_root.split(os.sep)
    if len(parts) > 0 and parts[0] in ('django_backend', 'staticfiles', 'mariadb-10.11.10', 'backend', '.git', '__pycache__', 'node_modules', 'staticfiles', 'assets', 'shared'):
        continue
    if not any(parts[0] == d for d in ('auth', 'buyer', 'seller', 'home', 'reports')):
        continue
    for f in files:
        if not f.endswith('.html'):
            continue
        fp = os.path.join(root, f)
        with open(fp, 'r', encoding='utf-8') as fh:
            content = fh.read()
        # Check for remaining root-relative paths
        bad = re.findall(r'(?:src|href)=[\"\']/(?:static|assets)/[^\"\']+', content)
        if bad:
            remaining += 1
            rel = os.path.relpath(fp, PROJECT)
            print(f"\n  ISSUES remaining in: {rel}")
            for b in bad:
                print(f"    {b}")

if remaining == 0:
    print("  No remaining broken paths found!")
