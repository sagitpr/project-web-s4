import os
import requests
import google.auth
from google.auth.transport.requests import Request

def get_auth_headers():
    print("Loading Google default credentials...")
    try:
        # Load default credentials. Google auth will automatically find the active gcloud user credentials.
        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "X-Goog-User-Project": "project-010f7e8f-fc0f-46fb-8c7"
        }
        print("Credentials loaded successfully!")
        return headers
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return {}

def download_assets():
    dest_dir = r"c:\Developer\project-web-s4\stitch_assets"
    os.makedirs(dest_dir, exist_ok=True)
    
    headers = get_auth_headers()
    if not headers:
        print("No auth headers available. Exiting.")
        return
    
    # 1. Fetch screen info JSON to get actual download URLs for html and image
    project_id = "2591679688399809280"
    screen_id = "4a97d4cbac3f4578bd4a599c16d81ba5"
    api_url = f"https://stitch.googleapis.com/v1/projects/{project_id}/screens/{screen_id}"
    
    print(f"Fetching screen info from {api_url}...")
    try:
        r = requests.get(api_url, headers=headers)
        print(f"Screen info response status: {r.status_code}")
        if r.status_code != 200:
            print("Failed to fetch screen info.")
            print(r.text[:1000])
            return
        
        data = r.json()
        print("Screen info fetched successfully!")
        
        html_url = data.get("htmlCode", {}).get("downloadUrl")
        image_url = data.get("screenshot", {}).get("downloadUrl")
        
        if not html_url or not image_url:
            print("Could not find downloadUrl in response. Keys in JSON:")
            print(data.keys())
            return
        
        # 3. Download HTML
        html_path = os.path.join(dest_dir, "screen.html")
        print(f"Downloading HTML from {html_url} to {html_path}...")
        # Note: download URLs may not need gcloud headers since they are public usercontent links, 
        # but let's request them simply.
        r_html = requests.get(html_url)
        if r_html.status_code == 200:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(r_html.text)
            print("Success: screen.html")
        else:
            print(f"Failed to download HTML, status code: {r_html.status_code}")
            
        # 4. Download Image
        image_path = os.path.join(dest_dir, "screenshot.png")
        print(f"Downloading image from {image_url} to {image_path}...")
        r_img = requests.get(image_url, stream=True)
        if r_img.status_code == 200:
            with open(image_path, "wb") as f:
                for chunk in r_img.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Success: screenshot.png")
        else:
            print(f"Failed to download image, status code: {r_img.status_code}")
            
    except Exception as e:
        print(f"Error during download process: {e}")

if __name__ == "__main__":
    download_assets()
