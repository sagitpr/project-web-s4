"""
SSH Fix Script for Warungio VPS Deployment
Usage: VPS_PASSWORD=your_password python scripts/ssh_fix.py

Fixes: Renames docker-compose.override.yml to docker-compose.dev.yml
and redeploys with production config.
"""
import paramiko, socket, time, sys, os

VPS_HOST = os.environ.get('VPS_HOST', '36.50.77.237')
VPS_USER = os.environ.get('VPS_USER', 'root')
VPS_PASSWORD = os.environ.get('VPS_PASSWORD', '')

if not VPS_PASSWORD:
    print("ERROR: Set VPS_PASSWORD environment variable")
    print("Usage: VPS_PASSWORD=your_password python scripts/ssh_fix.py")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def run_cmd(ssh, cmd, timeout=30, wait=2):
    """Run a command via SSH and print output safely."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    time.sleep(wait)
    out = stdout.read().decode('utf-8', errors='replace')
    safe = ''.join(c if ord(c) < 128 else '?' for c in out)
    print(safe.strip())
    print('---')

try:
    # Phase 1: Quick fix - just rename the override file
    print("=== PHASE 1: Remove override file ===")
    client.connect(VPS_HOST, port=22, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(30)

    run_cmd(client, 'cd /root/project-web-s4 && mv docker-compose.override.yml docker-compose.dev.yml && echo RENAME_OK', 10)
    run_cmd(client, 'ls -la /root/project-web-s4/docker-compose*.yml', 10)
    
    # Phase 2: Restart services with production config (no build, just restart)
    print("=== PHASE 2: Restart with production config ===")
    run_cmd(client, 
        'cd /root/project-web-s4 && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d',
        timeout=60, wait=10)
    
    # Phase 3: Verify
    print("=== PHASE 3: Verify production config ===")
    run_cmd(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"', 10)
    run_cmd(client, 'docker exec warungio-nginx grep -c "ssl" /etc/nginx/conf.d/warungio.conf', 10)
    run_cmd(client, 'docker exec warungio-nginx nginx -t 2>&1', 10)
    run_cmd(client, 'curl -sI http://localhost/ | head -5', 10)
    run_cmd(client, 'curl -skI https://localhost/ | head -5', 10)
    run_cmd(client, 'ss -tlnp | grep -E "443|80"', 10)

    client.close()
    print("FIX COMPLETE")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    try:
        transport = client.get_transport()
        if transport and transport.is_active():
            transport.close()
    except:
        pass
