#!/usr/bin/env python3
"""VPS: Copy missing premium.css and auth-ui.js from source to static volume."""
import paramiko, time, sys

HOST = "36.50.77.237"
USER = "root"
PASS = "Warungiosagit465!"

def ssh_run(cmd, timeout=60):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=22, username=USER, password=PASS, timeout=15,
              banner_timeout=15, auth_timeout=15, compress=True)
    t = c.get_transport()
    t.set_keepalive(30)
    chan = t.open_session()
    chan.settimeout(timeout)
    chan.exec_command(cmd)
    stdout = b""
    stderr = b""
    while True:
        if chan.recv_ready():
            stdout += chan.recv(4096)
        if chan.recv_stderr_ready():
            stderr += chan.recv_stderr(4096)
        if chan.exit_status_ready():
            break
        time.sleep(0.3)
    while chan.recv_ready():
        stdout += chan.recv(4096)
    while chan.recv_stderr_ready():
        stderr += chan.recv_stderr(4096)
    code = chan.recv_exit_status()
    c.close()
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), code

# Step 1: Copy missing CSS files from source to nginx volume
actions = [
    ("Copy premium.css to nginx volume",
     "docker cp /root/project-web-s4/django_backend/static/css/premium.css warungio-nginx:/app/staticfiles/css/premium.css && echo OK"),
    ("Copy auth-ui.js to nginx volume",
     "docker cp /root/project-web-s4/django_backend/static/js/utils/auth-ui.js warungio-nginx:/app/staticfiles/js/utils/auth-ui.js && echo OK"),
    ("Verify nginx volume has both files",
     "docker exec warungio-nginx sh -c 'ls -la /app/staticfiles/css/premium.css /app/staticfiles/js/utils/auth-ui.js 2>&1'"),
]

# Step 2: Rebuild container image with --no-cache for the django service
actions += [
    ("Rebuild django with --no-cache",
     "cd /root/project-web-s4 && docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache django 2>&1 | tail -5"),
    ("Restart django with new image",
     "cd /root/project-web-s4 && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d django 2>&1"),
]

for label, cmd in actions:
    print(f"\n=== {label} ===")
    out, err, code = ssh_run(cmd)
    if out.strip():
        print(out.strip()[:500])
    if err.strip():
        print(f"ERR: {err.strip()[:300]}")
    if code != 0:
        print(f"EXIT CODE: {code}")

# Step 3: Wait a bit then verify static files via HTTPS
print("\n=== WAITING 30s FOR DJANGO STARTUP ===")
time.sleep(30)

print("\n=== VERIFY FROM VPS (HTTPS localhost) ===")
for f in ["premium.css", "landing.css", "auth-ui.js"]:
    if f.endswith(".js"):
        url = f"/static/js/utils/{f}"
    else:
        url = f"/static/css/{f}"
    out, err, code = ssh_run(f"curl -sk -o /dev/null -w '%{{http_code}}' https://localhost{url}")
    print(f"  {url}: {out.strip()}")

# Step 4: Verify from public internet
print("\n=== VERIFY FROM VPS (HTTPS public domain) ===")
for url in ["/static/css/premium.css", "/static/css/landing.css", "/static/js/utils/auth-ui.js"]:
    out, err, code = ssh_run(f"curl -sk -o /dev/null -w '%{{http_code}}' https://warungio.web.id{url}")
    print(f"  {url}: {out.strip()}")
