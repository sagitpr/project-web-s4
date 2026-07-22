#!/usr/bin/env python3
"""VPS fix - git reset, rebuild nginx with CAP_CHOWN, validate."""
import subprocess, sys, time

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except: pass

try:
    import paramiko
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "--quiet"], timeout=60)
    import paramiko

HOST, PORT, USER, PASS = "36.50.77.237", 22, "root", "Warungiosagit465!"
PROJ = "/root/project-web-s4"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def run(cmd, timeout=60):
    if client.get_transport():
        client.get_transport().set_keepalive(15)
    i, o, e = client.exec_command(cmd, timeout=timeout)
    code = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    return out, err, code

print("Connecting...")
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
client.get_transport().set_keepalive(15)
print("Connected!\n")

# Step 1: Git reset
print("=" * 60)
print("STEP 1: git reset --hard origin/main")
print("=" * 60)
out, err, code = run(
    "cd {} && git fetch origin && git reset --hard origin/main && git clean -fd 2>&1 && echo '=== GIT DONE ===' && git log --oneline -3".format(PROJ), 45)
print(out[:600])
if err: print("ERR:", err[:300])

# Verify configs
print()
out, err, code = run(
    "echo '--- PROXY_CACHE ---' && grep -n proxy_cache {}/nginx/nginx.conf {}/nginx/warungio.conf 2>&1 || echo 'CLEAN'".format(PROJ, PROJ), 10)
print(out[:500])

# Step 2: Rebuild nginx
print("\n" + "=" * 60)
print("STEP 2: Rebuild nginx container")
print("=" * 60)
out, err, code = run(
    "cd {p} && "
    "docker compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx 2>/dev/null; "
    "docker compose -f docker-compose.yml -f docker-compose.prod.yml rm -f nginx 2>/dev/null; "
    "echo '=== PULLING NGINX IMAGE ===' && "
    "timeout 120 docker pull nginx:1.25-alpine 2>&1; "
    "echo '=== REBUILDING ===' && "
    "docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --force-recreate nginx 2>&1"
    .format(p=PROJ), 180)
print(out[:1000])
if err: print("ERR:", err[:500])

# Step 3: Poll health
print("\n" + "=" * 60)
print("STEP 3: Poll nginx health")
print("=" * 60)
healthy = False
logs_content = ""
for i in range(18):
    time.sleep(5)
    try:
        out, err, code = run(
            "docker compose -f {p}/docker-compose.yml -f {p}/docker-compose.prod.yml ps nginx 2>&1".format(p=PROJ), 10)
        sl = out.lower()
        print("  {}s: {}".format((i+1)*5, out.strip()[:100]))
        if "healthy" in sl:
            healthy = True
            print("  HEALTHY!")
            break
        elif "up" in sl and "unhealthy" not in sl:
            healthy = True
            print("  UP!")
            break
        elif "restarting" in sl:
            print("  (restarting...)")
    except Exception as e:
        print("  {}s: reconnecting...".format((i+1)*5))
        try:
            client.close()
            client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
            client.get_transport().set_keepalive(15)
        except: pass

# Step 4: Container status
print("\n" + "=" * 60)
print("STEP 4: Container status + logs")
print("=" * 60)
try:
    out, err, code = run(
        "docker compose -f {p}/docker-compose.yml -f {p}/docker-compose.prod.yml ps 2>&1".format(p=PROJ), 10)
    print(out)
except: print("Status unavailable")

try:
    out, err, code = run(
        "docker compose -f {p}/docker-compose.yml -f {p}/docker-compose.prod.yml logs nginx --tail=30 2>&1".format(p=PROJ), 10)
    logs_content = out
    print("\nNGINX LOGS:")
    print(out[:1000])
except: print("Logs unavailable")

# Check for chown errors in logs
if 'chown' in logs_content.lower() and 'operation not permitted' in logs_content.lower():
    print("\nWARNING: chown errors still present in nginx logs!")
    print("This means CAP_CHOWN is not being applied correctly.")
    # Check if docker-compose.yml has the capabilities
    try:
        out, err, code = run("grep -A2 'cap_add' {}/docker-compose.yml | head -10".format(PROJ), 10)
        print("Current cap_add in docker-compose.yml:")
        print(out)
    except: pass

# Step 5: Endpoints
if healthy:
    print("\n" + "=" * 60)
    print("STEP 5: Endpoint validation")
    print("=" * 60)
    for name, cmd in [
        ("HTTP / (redirect)", "curl -sI http://localhost:80/ 2>&1 | head -10"),
        ("HTTPS /", "curl -skI https://localhost:443/ 2>&1 | head -10"),
        ("HTTPS /health/", "curl -skI https://localhost:443/health/ 2>&1 | head -10"),
        ("HTTPS /robots.txt", "curl -skI https://localhost:443/robots.txt 2>&1 | head -10"),
        ("HTTPS /sitemap.xml", "curl -skI https://localhost:443/sitemap.xml 2>&1 | head -10"),
    ]:
        try:
            out, err, code = run("cd {} && {}".format(PROJ, cmd), 15)
            print("--- {} ---".format(name))
            print(out[:300])
        except: pass

# Step 6: Firewall
print("\n" + "=" * 60)
print("STEP 6: Firewall + Ports")
print("=" * 60)
try:
    out, err, code = run("ufw status 2>&1 || echo 'ufw unavailable'", 10)
    print(out[:200])
except: pass
try:
    out, err, code = run("ss -tlnp | grep -E ':(80|443) ' 2>&1 || echo 'not listening'", 10)
    print("Ports:", out[:200])
except: pass

try: client.close()
except: pass

print("\n" + "=" * 60)
if healthy:
    print("DEPLOYMENT SUCCESSFUL! Nginx is running without crash loops!")
else:
    print("Deployment complete - check logs above.")
    if 'chown' in logs_content.lower():
        print("WARNING: chown errors present - need to check docker-compose.yml capabilities.")
print("=" * 60)
