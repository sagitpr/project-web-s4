#!/usr/bin/env python3
"""VPS: run collectstatic, verify static files, check nginx logs."""
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

# 1. Check Django logs for collectstatic
print("=== 1. DJANGO LOGS (first 20 lines) ===")
out, err, code = ssh_run("docker logs warungio-django 2>&1 | head -20")
print(out)

# 2. Check source CSS files in container
print("\n=== 2. SOURCE CSS FILES ===")
out, err, code = ssh_run("docker exec warungio-django ls /app/django_backend/static/css/")
print(out)

# 3. Check source JS utils in container
print("\n=== 3. SOURCE JS UTILS ===")
out, err, code = ssh_run("docker exec warungio-django ls /app/django_backend/static/js/utils/")
print(out)

# 4. Run collectstatic
print("\n=== 4. RUNNING COLLECTSTATIC ===")
out, err, code = ssh_run("docker exec warungio-django python manage.py collectstatic --noinput 2>&1 | grep -E 'copied|found'")
print(out)

# 5. Verify premium.css and auth-ui.js in nginx volume
print("\n=== 5. NGINX VOLUME CSS ===")
out, err, code = ssh_run("docker exec warungio-nginx ls -la /app/staticfiles/css/")
print(out)

print("\n=== 6. NGINX VOLUME JS ===")
out, err, code = ssh_run("docker exec warungio-nginx ls -la /app/staticfiles/js/utils/ 2>&1")
print(out)

# 7. Verify via HTTPS on VPS
print("\n=== 7. HTTPS STATIC FILES ON VPS ===")
for f in ["premium.css", "landing.css", "style.css", "tokens.css"]:
    out, err, code = ssh_run("curl -sk -o /dev/null -w '%{http_code}' https://localhost/static/css/" + f)
    print(f"  css/{f}: {out.strip()}")
out, err, code = ssh_run("curl -sk -o /dev/null -w '%{http_code}' https://localhost/static/js/utils/auth-ui.js")
print(f"  auth-ui.js: {out.strip()}")

# 8. Verify from public internet
print("\n=== 8. HTTPS FROM PUBLIC ===")
import socket
s = socket.socket()
s.settimeout(5)
r = s.connect_ex(("36.50.77.237", 443))
print(f"  Port 443: {'OPEN' if r == 0 else 'CLOSED'}")
s.close()
s = socket.socket()
s.settimeout(5)
r = s.connect_ex(("36.50.77.237", 80))
print(f"  Port 80: {'OPEN' if r == 0 else 'CLOSED'}")
s.close()

print("\n=== 9. NGINX LOGS (last 10) ===")
out, err, code = ssh_run("docker logs warungio-nginx --tail=10 2>&1 | grep -iE 'error|404|static' || echo NO_ERRORS")
print(out)
