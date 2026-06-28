import subprocess
def run():
    res = subprocess.run([
        'gcloud', 'run', 'deploy', 'warungio',
        '--image=asia-southeast2-docker.pkg.dev/project-010f7e8f-fc0f-46fb-8c7/warungio/warungio:latest',
        '--region=asia-southeast2'
    ], capture_output=True, text=True, shell=True)
    with open('deploy_output.txt', 'w', encoding='utf-8') as f:
        f.write("STDOUT:\n" + res.stdout + "\nSTDERR:\n" + res.stderr)
if __name__ == '__main__':
    run()
