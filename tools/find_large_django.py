import os

def check():
    sizes = []
    for root, dirs, files in os.walk('django_backend'):
        # Get total size of files in this directory (shallow)
        dir_size = 0
        for f in files:
            p = os.path.join(root, f)
            try:
                dir_size += os.path.getsize(p)
            except OSError:
                pass
        if dir_size > 0:
            sizes.append((root, dir_size / (1024 * 1024)))
            
    sizes.sort(key=lambda x: x[1], reverse=True)
    print("Top subdirectories in django_backend by size:")
    for path, size in sizes[:15]:
        print(f"  {path}: {size:.2f} MB")

if __name__ == '__main__':
    check()
