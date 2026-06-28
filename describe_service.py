import subprocess
def run():
    res = subprocess.run(['gcloud', 'run', 'services', 'describe', 'warungio', '--region=asia-southeast2'], capture_output=True, text=True, shell=True)
    with open('service_describe.txt', 'w', encoding='utf-8') as f:
        f.write("STDOUT:\n" + res.stdout + "\nSTDERR:\n" + res.stderr)
if __name__ == '__main__':
    run()
