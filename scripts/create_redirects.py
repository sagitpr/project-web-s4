import os
import shutil

BASE = '.'

# Mapping: old_dir -> new_path (relative URL target)
REDIRECTS = {
    'login': 'auth/login',
    'Daftar': 'auth/register',
    'Daftar_mitra': 'auth/register-mitra',
    'beranda': 'buyer/dashboard',
    'beranda_penjual': 'seller/dashboard',
    'otp': 'auth/otp',
    'reset_password': 'auth/reset-password',
    'pesanan': 'buyer/orders',
    'my_product': 'seller/products',
    'panduan_mitra': 'seller/partner-guide',
    'laporan': 'reports',
    'social-callback': 'auth/callback',
}

REDIRECT_TEMPLATE = '''<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <title>Mengalihkan...</title>
  <link rel="canonical" href="{target}">
</head>
<body>
  <p>Mengalihkan ke <a href="{target}">{target}</a>...</p>
</body>
</html>'''

for old_dir, new_path in REDIRECTS.items():
    full_old = os.path.join(BASE, old_dir, 'index.html')
    full_new = os.path.join(BASE, old_dir)
    
    if not os.path.exists(os.path.join(BASE, old_dir)):
        print(f"SKIP: {old_dir}/ not found")
        continue
    
    target = f'../{new_path}/index.html'
    
    # Backup original index.html first
    bak_path = full_old + '.bak'
    if os.path.exists(full_old) and not os.path.exists(bak_path):
        shutil.copy2(full_old, bak_path)
        print(f"BACKUP: {full_old} -> {bak_path}")
    
    # If it's social-callback, also handle apple.html
    if old_dir == 'social-callback':
        # Create the subdir if needed
        os.makedirs(os.path.join(BASE, 'auth', 'callback'), exist_ok=True)
        old_apple = os.path.join(BASE, old_dir, 'apple.html')
        new_apple = os.path.join(BASE, 'auth', 'callback', 'apple.html')
        if os.path.exists(old_apple) and not os.path.exists(new_apple):
            shutil.copy2(old_apple, new_apple)
            print(f"COPIED: {old_apple} -> {new_apple}")
        # Create redirect at original location
        target_apple = f'../{new_path}/apple.html'
        redirect_content = REDIRECT_TEMPLATE.replace('{target}', target_apple)
        # Write apple.html redirect
        apple_redirect = os.path.join(BASE, old_dir, 'apple.html')
        with open(apple_redirect, 'w') as f:
            f.write(redirect_content)
        print(f"REDIRECT: {old_dir}/apple.html -> {target_apple}")
    
    # Write redirect for index.html
    redirect_content = REDIRECT_TEMPLATE.replace('{target}', target)
    with open(full_old, 'w') as f:
        f.write(redirect_content)
    print(f"REDIRECT: {full_old} -> {target}")

# Also create redirect at root-level index.html if it doesn't exist
root_index = os.path.join(BASE, 'index.html')
if not os.path.exists(root_index):
    root_redirect = '''<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=home/index.html">
  <title>Warungio</title>
</head>
<body>
  <p>Selamat datang di Warungio. <a href="home/index.html">Masuk ke Beranda</a></p>
</body>
</html>'''
    with open(root_index, 'w') as f:
        f.write(root_redirect)
    print(f"CREATED: root index.html -> home/index.html")

print("\\nDone! All redirect pages created.")
