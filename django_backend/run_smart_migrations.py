import os
import sys
import subprocess

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Running: python manage.py sync_migrations")
    res = subprocess.run(
        [sys.executable, "manage.py", "sync_migrations"],
        text=True
    )
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
