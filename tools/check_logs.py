import subprocess

def check():
    cmd = ['gcloud', 'logging', 'read', 'resource.type=cloud_run_revision AND resource.labels.service_name=warungio AND severity>=WARNING', '--limit=20', '--format=json']
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    with open('cloudrun_logs.txt', 'w', encoding='utf-8') as f:
        f.write("STDOUT:\n")
        f.write(res.stdout)
        f.write("\nSTDERR:\n")
        f.write(res.stderr)

if __name__ == '__main__':
    check()
