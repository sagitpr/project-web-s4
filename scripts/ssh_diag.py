"""
SSH Diagnostic Script for Warungio VPS
Usage: VPS_PASSWORD=your_password python scripts/ssh_diag.py

Diagnoses Docker, Nginx, and port status on the VPS.
"""
import paramiko, socket, time, sys, os

VPS_HOST = os.environ.get('VPS_HOST', '36.50.77.237')
VPS_USER = os.environ.get('VPS_USER', 'root')
VPS_PASSWORD = os.environ.get('VPS_PASSWORD', '')

if not VPS_PASSWORD:
    print("ERROR: Set VPS_PASSWORD environment variable")
    print("Usage: VPS_PASSWORD=your_password python scripts/ssh_diag.py")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(VPS_HOST, port=22, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(30)

    commands = [
        'echo "=== NGINX CONFIG ==="',
        'docker exec warungio-nginx head -5 /etc/nginx/conf.d/warungio.conf 2>&1',
        'echo "=== NGINX TEST ==="',
        'docker exec warungio-nginx nginx -t 2>&1',
        'echo "=== NGINX LOGS ==="',
        'docker logs warungio-nginx 2>&1 | tail -20',
        'echo "=== COMPOSE FILES ==="',
        'ls -la /root/project-web-s4/docker-compose.override.yml 2>&1; echo "---"; ls -la /root/project-web-s4/docker-compose.dev.yml 2>&1',
        'echo "=== DOCKER PS ==="',
        'cd /root/project-web-s4 && docker compose ps 2>&1',
        'echo "=== PORT LISTENERS ==="',
        'ss -tlnp 2>&1 | head -10',
    ]

    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        time.sleep(1)
        out = stdout.read().decode('utf-8', errors='replace')
        safe = ''.join(c if ord(c) < 128 else '?' for c in out)
        print(safe.strip())
        print('---')

    client.close()
    print("DIAGNOSTIC COMPLETE")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
