#!/usr/bin/env python3
"""VPS deploy: git pull, build, restart, wait, validate static files."""
import paramiko, time, sys, socket

HOST = "36.50.77.237"
USER = "root"
PASS = "Warungiosagit465!"

def ssh_run(cmd, timeout=300):
    """Run command on VPS with long timeout. Returns stdout."""
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
        time.sleep(0.5)
    
    # Read any remaining data
    while chan.recv_ready():
        stdout += chan.recv(4096)
    while chan.recv_stderr_ready():
        stderr += chan.recv_stderr(4096)
    
    exit_code = chan.recv_exit_status()
    c.close()
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), exit_code

def main():
    # 1. Git pull
    print("=== 1. GIT PULL ===")
    out, err, code = ssh_run("cd /root/project-web-s4 && git fetch origin && git reset --hard origin/main && echo GIT_HASH: $(git log -1 --oneline)", timeout=60)
    print(out[-500:])
    if err: print("ERR:", err[-300:])
    
    # 2. Docker build + up
    print("\n=== 2. DOCKER BUILD & RESTART ===")
    print("This will take 2-5 minutes...")
    out, err, code = ssh_run("cd /root/project-web-s4 && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build 2>&1", timeout=600)
    print(out[-2000:])
    if err: print("ERR:", err[-500:])
    
    # 3. Wait for health
    print("\n=== 3. WAIT FOR HEALTH ===")
    time.sleep(60)
    healthy = False
    for i in range(20):
        out, _, _ = ssh_run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health/ 2>&1", timeout=15)
        code = out.strip()
        print(f"  Attempt {i+1}/20: {code}")
        if code == "200":
            healthy = True
            print("  Healthy!")
            break
        time.sleep(10)
    
    if not healthy:
        print("  WARNING: Health check did not return 200")
    
    # 4. Verify static files
    print("\n=== 4. VERIFY STATIC FILES ===")
    files = [
        "/static/css/premium.css",
        "/static/js/utils/auth-ui.js",
        "/static/css/landing.css",
        "/static/css/tokens.css",
        "/static/css/components.css",
    ]
    for f in files:
        out, _, _ = ssh_run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost{f} 2>&1", timeout=15)
        status = "✅" if out.strip() == "200" else "❌"
        print(f"  {status} {f}: {out.strip()}")
    
    # 5. Container status
    print("\n=== 5. CONTAINERS ===")
    out, _, _ = ssh_run("docker ps --format '{{.Names}}: {{.Status}}'", timeout=15)
    print(out)

if __name__ == "__main__":
    main()
