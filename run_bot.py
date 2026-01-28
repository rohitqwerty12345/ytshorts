import os
import pickle
import base64
import random
import yt_dlp
import static_ffmpeg
from moviepy import VideoFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# SETTINGS
# ==========================================
KEYWORDS = [
    "luxury travel shorts", "budget travel hacks", "hidden gems europe",
    "solo travel adventure", "travel photography tips", "bali island life",
    "tokyo street food", "tropical paradise vlog"
]
MY_KEYWORD = random.choice(KEYWORDS)
MY_CHANNEL_NAME = "VoyageSpotlight"
OUTRO_PATH = "outro.mp4"
# ==========================================

def get_youtube_clients():
    """Initializes API clients and prepares environment."""
    api_key = os.environ.get('YOUTUBE_API_KEY')
    client_secrets_json = os.environ.get('YOUTUBE_CLIENT_SECRETS')
    token_b64 = os.environ.get('YOUTUBE_TOKEN_PICKLE')
    
    # Write temporary credential files
    with open('client_secrets.json', 'w') as f: f.write(client_secrets_json)
    with open('token.pickle', 'wb') as f: f.write(base64.b64decode(token_b64))
    
    # Write cookies if available
    cookie_data = os.environ.get('YOUTUBE_COOKIES')
    if cookie_data:
        with open('cookies.txt', 'w') as f: f.write(cookie_data)

    search_client = build("youtube", "v3", developerKey=api_key)
    with open('token.pickle', 'rb') as f: creds = pickle.load(f)
    upload_client = build("youtube", "v3", credentials=creds)
    
    return search_client, upload_client

def download_with_fallback(url, output_name):
    """Tries downloading with browser spoofing first, then falls back to cookies."""
    opts = {
        'quiet': True,
        'outtmpl': output_name,
        'format': 'bestvideo[height<=1080]+bestaudio/best[ext=m4a]/best',
        'merge_output_format': 'mp4',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Try 1: Clean Download
    try:
        print("[DOWNLOAD] Attempting download without cookies...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
            return True
    except:
        print("[DOWNLOAD] Blocked. Retrying with YOUTUBE_COOKIES...")

    # Try 2: Cookie Download
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                return True
        except Exception as e:
            print(f"[ERROR] All download attempts failed: {e}")
    return False

def main():
    print(f"--- STARTING SMART AUTO-BOT (Keyword: {MY_KEYWORD}) ---")
    static_ffmpeg.add_paths()
    search_client, upload_client = get_youtube_clients()

    # 1. Search via API
    request = search_client.search().list(q=MY_KEYWORD, part="snippet", maxResults=10, type="video", videoDuration="short")
    results = request.execute()
    
    target_url = None
    video_info = None

    for item in results.get("items", []):
        v_id = item["id"]["videoId"]
        temp_url = f"https://www.youtube.com/watch?v={v_id}"
        
        # Verify duration
        with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None}) as ydl:
            try:
                info = ydl.extract_info(temp_url, download=False)
                if 0 < info.get('duration', 0) <= 60:
                    target_url = temp_url
                    video_info = info
                    break
            except: continue

    if not target_url:
        print("[ERROR] No valid videos found. Cookies may be expired.")
        return

    # 2. Download
    if not download_with_fallback(target_url, "raw.mp4"):
        return

    # 3. Process Video
    print("[EDITING] Stitching outro...")
    creator = video_info.get('uploader', 'Creator')
    clip = VideoFileClip("raw.mp4")
    outro = VideoFileClip(OUTRO_PATH).resized(height=clip.h).with_fps(clip.fps)
    
    final = concatenate_videoclips([clip, outro])
    final.write_videofile("READY.mp4", codec="libx264", audio_codec="aac")

    # 4. Final Upload
    prefix = f"Org by [@{creator}] | "
    suffix = f" | {MY_CHANNEL_NAME}"
    title = f"{prefix}{video_info.get('title', '')[:(100-len(prefix)-len(suffix))]}{suffix}"
    
    print(f"[UPLOAD] Posting: {title}")
    body = {
        'snippet': {'title': title, 'description': f"Original content by {creator}.", 'categoryId': '22'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload("READY.mp4", chunksize=-1, resumable=True)
    upload_client.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    
    # 5. Cleanup
    clip.close()
    outro.close()
    for f in ["raw.mp4", "READY.mp4", "cookies.txt", "token.pickle", "client_secrets.json"]:
        if os.path.exists(f): os.remove(f)
    print("[SUCCESS] Bot finished task.")

if __name__ == "__main__":
    main()
