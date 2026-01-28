import os
import pickle
import base64
import random
import yt_dlp
import static_ffmpeg
from moviepy import VideoFileClip, concatenate_videoclips
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# ROTATIONAL KEYWORDS & SETTINGS
# ==========================================
KEYWORDS = [
    "luxury travel shorts", "budget travel hacks", "hidden gems europe",
    "solo travel adventure", "travel photography tips", "bali island life",
    "tokyo street food", "tropical paradise vlog", "mountain hiking aesthetic",
    "safari wildlife moments"
]
MY_KEYWORD = random.choice(KEYWORDS)
MY_CHANNEL_NAME = "VoyageSpotlight"
OUTRO_PATH = "outro.mp4"
# ==========================================

def get_youtube_clients():
    """Initializes both the Search (API Key) and Upload (OAuth) clients"""
    # 1. Retrieve secrets from GitHub environment
    api_key = os.environ.get('YOUTUBE_API_KEY')
    client_secrets_json = os.environ.get('YOUTUBE_CLIENT_SECRETS')
    token_b64 = os.environ.get('YOUTUBE_TOKEN_PICKLE')
    
    # Reconstruct local files for the libraries to read
    with open('client_secrets.json', 'w') as f: f.write(client_secrets_json)
    with open('token.pickle', 'wb') as f: f.write(base64.b64decode(token_b64))
    
    # Build the Search Client (uses API Key)
    search_client = build("youtube", "v3", developerKey=api_key)
    
    # Build the Upload Client (uses OAuth Token)
    with open('token.pickle', 'rb') as f: creds = pickle.load(f)
    upload_client = build("youtube", "v3", credentials=creds)
    
    return search_client, upload_client

def find_video_id(search_client, keyword):
    """Uses the official Search API to find a Short under 60s"""
    print(f"[API] Searching for: {keyword}")
    request = search_client.search().list(
        q=keyword,
        part="snippet",
        maxResults=10,
        type="video",
        videoDuration="short" # API limit for 'short' is < 4 mins
    )
    response = request.execute()

    for item in response.get("items", []):
        v_id = item["id"]["videoId"]
        url = f"https://www.youtube.com/watch?v={v_id}"
        
        # Exact duration check with yt-dlp
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if 0 < info.get('duration', 0) <= 60:
                    print(f"[MATCH] Valid Short found: {url}")
                    return url
            except: continue
    return None

def main():
    print(f"--- STARTING API-DRIVEN AUTO BOT ---")
    print(f"Target Keyword: {MY_KEYWORD}")
    static_ffmpeg.add_paths()
    
    search_client, upload_client = get_youtube_clients()

    # 1. Search for a video ID
    target_url = find_video_id(search_client, MY_KEYWORD)
    if not target_url:
        print("[ERROR] No suitable videos found for this keyword.")
        return

    # 2. Download high quality
    ydl_opts = {'quiet': True, 'format': 'bestvideo+bestaudio/best', 'outtmpl': 'raw_download.%(ext)s'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target_url, download=True)
        raw_file = ydl.prepare_filename(info)
        creator = info.get('uploader', 'Creator')

    # 3. Generate Title (100 char limit)
    prefix = f"Org by [@{creator}] | "
    suffix = f" | {MY_CHANNEL_NAME}"
    clean_title = info.get('title', 'Travel Highlight')
    title_text = f"{prefix}{clean_title[:(100-len(prefix)-len(suffix))]}{suffix}"

    # 4. Stitch with MoviePy 2.0
    print("[EDITING] Stitching outro...")
    clip = VideoFileClip(raw_file)
    outro = VideoFileClip(OUTRO_PATH).resized(height=clip.h).with_fps(clip.fps)
    final = concatenate_videoclips([clip, outro])
    final_path = "FINAL_UPLOAD.mp4"
    final.write_videofile(final_path, codec="libx264", audio_codec="aac")

    # 5. Official Upload
    print(f"[UPLOAD] Posting to YouTube: {title_text}")
    request_body = {
        'snippet': {
            'title': title_text,
            'description': f"Support the creator: {creator}! Promoting amazing travel talent.",
            'tags': ['shorts', 'travel'],
            'categoryId': '22'
        },
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(final_path, chunksize=-1, resumable=True)
    upload_client.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    
    # Cleanup
    clip.close()
    outro.close()
    print("[SUCCESS] Process Complete!")

if __name__ == "__main__":
    main()
