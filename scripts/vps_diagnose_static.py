#!/usr/bin/env python3
"""VPS diagnostic: check why premium.css and auth-ui.js are missing from static volume."""
import paramiko, time

HOST = "36.50.77.237"
USER = "root"
PASS = "Warungiosagit465!"

def ssh_run(cmd, timeout=30):
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

actions = [
    ("VPS source CSS files", "ls /root/project-web-s4/django_backend/static/css/"),
    ("VPS source JS utils", "ls /root/project-web-s4/django_backend/static/js/utils/"),
    ("Inside django container: static dir", "docker exec warungio-django ls /app/django_backend/static/ 2>&1"),
    ("Inside django container: django_backend dir", "docker exec warungio-django ls /app/django_backend/ 2>&1 | head -20"),
    ("Inside django container: check STATICFILES_DIRS path", "docker exec warungio-django sh -c 'test -d /app/django_backend/static && echo EXISTS || echo MISSING'"),
    ("Inside django container: check premium.css", "docker exec warungio-django sh -c 'test -f /app/django_backend/static/css/premium.css && echo EXISTS || echo MISSING'"),
    ("Inside django container: check auth-ui.js", "docker exec warungio-django sh -c 'test -f /app/django_backend/static/js/utils/auth-ui.js && echo EXISTS || echo MISSING'"),
    ("Nginx volume CSS", "docker exec warungio-nginx ls /app/staticfiles/css/ 2>&1"),
    ("Nginx volume JS utils", "docker exec warungio-nginx ls /app/staticfiles/js/utils/ 2>&1"),
    ("Django logs (collectstatic)", "docker logs warungio-django 2>&1 | grep -iE 'collectstatic|static' || echo NO_STATIC_LOG"),
]

for label, cmd in actions:
    print(f"\n=== {label} ===")
    out, err, code = ssh_run(cmd)
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"ERR: {err.strip()}")
