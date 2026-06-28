import os
import shutil
import hashlib

def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def move_and_deduplicate_images(source_dirs, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    target_hashes = {}
    # Scan target dir first
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                path = os.path.join(root, file)
                target_hashes[file] = get_file_hash(path)

    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            continue
        
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                    source_path = os.path.join(root, file)
                    target_path = os.path.join(target_dir, file)
                    
                    source_hash = get_file_hash(source_path)
                    
                    if file in target_hashes:
                        if source_hash == target_hashes[file]:
                            print(f"Duplicate found and deleting: {source_path}")
                            os.remove(source_path)
                        else:
                            # Same name, different content. Rename or skip? 
                            # User said "If a file already exists ... you can just delete the duplicate"
                            # Usually this implies same content. If different content, maybe it's a different image with same name.
                            # For safety, I'll append a hash if it's different.
                            new_name = f"{os.path.splitext(file)[0]}_{source_hash[:8]}{os.path.splitext(file)[1]}"
                            target_path = os.path.join(target_dir, new_name)
                            print(f"Conflict found (different content), moving to: {target_path}")
                            shutil.move(source_path, target_path)
                    else:
                        print(f"Moving: {source_path} to {target_path}")
                        shutil.move(source_path, target_path)
                        target_hashes[file] = source_hash

def move_remaining_assets(source_assets, target_static_assets):
    if not os.path.exists(source_assets):
        return
    
    if not os.path.exists(target_static_assets):
        os.makedirs(target_static_assets, exist_ok=True)
        
    for item in os.listdir(source_assets):
        s = os.path.join(source_assets, item)
        d = os.path.join(target_static_assets, item)
        if os.path.isdir(s):
            if os.path.exists(d):
                # Merge directories
                for root, dirs, files in os.walk(s):
                    dest_root = root.replace(s, d, 1)
                    if not os.path.exists(dest_root):
                        os.makedirs(dest_root)
                    for file in files:
                        sh_file = os.path.join(root, file)
                        dh_file = os.path.join(dest_root, file)
                        if not os.path.exists(dh_file):
                            shutil.move(sh_file, dh_file)
                        else:
                            os.remove(sh_file) # Already exists
            else:
                shutil.move(s, d)
        else:
            if not os.path.exists(d):
                shutil.move(s, d)
            else:
                os.remove(s)

if __name__ == "__main__":
    base_dir = r"C:\Developer\project-web-s4"
    target_images = os.path.join(base_dir, "django_backend", "static", "images")
    
    # Source image directories to check
    image_sources = [
        os.path.join(base_dir, "assets", "images"),
        os.path.join(base_dir, "src", "assets", "images"),
        os.path.join(base_dir, "staticfiles", "images"),
    ]
    
    # Also look for images in other places mentioned or found
    # The user mentioned 'other locations'. I'll search for images in directories I'm about to delete.
    other_sources = ["auth", "buyer", "home", "seller", "reports", "backend"]
    for src in other_sources:
        image_sources.append(os.path.join(base_dir, src))

    print("Moving and deduplicating images...")
    move_and_deduplicate_images(image_sources, target_images)
    
    print("Standardizing assets folder...")
    move_remaining_assets(os.path.join(base_dir, "assets"), os.path.join(base_dir, "django_backend", "static", "assets"))
    
    print("Done.")
