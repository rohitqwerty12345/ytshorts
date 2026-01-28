import asyncio
import os
import pickle
import base64
import random
from playwright.async_api import async_playwright
import yt_dlp
import static_ffmpeg
from moviepy import VideoFileClip, concatenate_videoclips
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

def get_youtube_client():
    # Retrieve secrets from GitHub environment
    client_secrets_json = os.environ.get('YOUTUBE_CLIENT_SECRETS')
    token_b64 = os.environ.get('YOUTUBE_TOKEN_PICKLE')
    
    # Reconstruct files for the API
    with open('client_secrets.json', 'w') as f: f.write(client_secrets_json)
    with open('token.pickle', 'wb') as f: f.write(base64.b64decode(token_b64))
    
    with open('token.pickle', 'rb') as f: creds = pickle.load(f)
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(youtube, file_path, title, description):
    print(f"[UPLOAD] Posting: {title}")
    request_body = {
        'snippet': {'title': title, 'description': description, 'tags': ['shorts'], 'categoryId': '22'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"[SUCCESS] Video Uploaded! ID: {response.get('id')}")

async def run_automation():
    print(f"--- CLOUD MODE ACTIVE: Keyword [{MY_KEYWORD}] ---")
    static_ffmpeg.add_paths()
    youtube = get_youtube_client()

    async with async_playwright() as p:
        # Mandatory: headless=True for GitHub Actions
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(f"https://www.youtube.com/results?search_query={MY_KEYWORD}&sp=EgYIARAB")
        
        # Aggressive selector for any video link in a Shorts format
        short_selector = "a[href*='/shorts/']"
        await page.wait_for_selector(short_selector, timeout=60000)
        
        all_links = await page.locator(short_selector).all()
        target_url = None
        for link in all_links:
            href = await link.get_attribute("href")
            if href and len(href.strip("/")) > 7:
                target_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
                break

        if not target_url: return

        # Process the Video
        with yt_dlp.YoutubeDL({'quiet': True, 'javascript_runtime': 'node'}) as ydl:
            info = ydl.extract_info(target_url, download=True)
            raw_file = ydl.prepare_filename(info)
            creator = info.get('uploader', 'Creator')
            
            # Title Logic (100 char limit)
            prefix = f"Org by [@{creator}] | "
            suffix = f" | {MY_CHANNEL_NAME}"
            title_text = f"{prefix}{info.get('title', '')[:(100-len(prefix)-len(suffix))]}{suffix}"
            
            # Stitch with Outro
            clip = VideoFileClip(raw_file)
            outro = VideoFileClip(OUTRO_PATH).resized(height=clip.h).with_fps(clip.fps)
            final = concatenate_videoclips([clip, outro])
            final_path = "UPLOAD_READY.mp4"
            final.write_videofile(final_path, codec="libx264", audio_codec="aac")

            # Final Upload
            upload_to_youtube(youtube, final_path, title_text, f"Original by {creator}. Promoting amazing talent!")
            
            clip.close()
            outro.close()
            if os.path.exists(raw_file): os.remove(raw_file)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_automation())
