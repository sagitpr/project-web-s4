import subprocess

def check():
    cmd = ['gcloud', 'builds', 'list', '--limit=5']
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    with open('builds.txt', 'w') as f:
        f.write("STDOUT:\n")
        f.write(res.stdout)
        f.write("\nSTDERR:\n")
        f.write(res.stderr)

if __name__ == '__main__':
    check()
