"""VPS SSH connectivity check + system resource audit."""
import paramiko
import socket
import sys
import time

HOST = '36.50.77.237'
PORT = 22
USER = 'root'
PASS = 'Warungiosagit465!'

def port_scan():
    print("=" * 50)
    print("VPS PORT SCAN")
    print("=" * 50)
    for port in [22, 80, 443, 8000, 6379, 3306]:
        s = socket.socket()
        s.settimeout(5)
        try:
            result = s.connect_ex((HOST, port))
            status = "OPEN" if result == 0 else "CLOSED"
            print(f"  Port {port:5d}: {status}")
        except Exception as e:
            print(f"  Port {port:5d}: ERROR - {e}")
        finally:
            s.close()

def try_ssh():
    print()
    print("=" * 50)
    print("SSH CONNECTION ATTEMPT")
    print("=" * 50)
    
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for attempt in range(3):
        try:
            print(f"\n  Attempt {attempt + 1}/3...")
            c.connect(
                HOST, port=PORT, username=USER, password=PASS,
                timeout=20, banner_timeout=20, auth_timeout=20,
                compress=True, look_for_keys=False, allow_agent=False
            )
            t = c.get_transport()
            t.set_keepalive(30)
            print("  ✅ SSH CONNECTED!")
            
            # Run diagnostics
            commands = [
                "free -h",
                "echo '---'",
                "df -h /",
                "echo '---'",
                "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo 'Docker not available'",
                "echo '---'",
                "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'No ss/netstat'",
                "echo '---'",
                "uptime",
                "echo '---'",
                "dmesg | tail -20 2>/dev/null || echo 'Cannot read dmesg'"
            ]
            cmd = " && ".join(commands)
            stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode(errors='replace')
            print(output)
            if exit_code != 0:
                err = stderr.read().decode(errors='replace')
                if err.strip():
                    print(f"  Stderr: {err[:500]}")
            c.close()
            return True
            
        except paramiko.AuthenticationException:
            print("  ❌ SSH Authentication FAILED")
            return False
        except socket.timeout:
            print("  ❌ SSH Connection TIMEOUT (daemon hung - OOM)")
        except Exception as e:
            print(f"  ❌ SSH Error: {type(e).__name__}: {e}")
        
        if attempt < 2:
            print("  Retrying in 5 seconds...")
            time.sleep(5)
    
    print("\n  ❌ SSH UNREACHABLE after 3 attempts")
    print("  → VPS needs HARD REBOOT from provider console")
    return False

if __name__ == '__main__':
    port_scan()
    try_ssh()
