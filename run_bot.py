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
# ROTATIONAL KEYWORDS
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
    
    # Write them to temporary files
    with open('client_secrets.json', 'w') as f: f.write(client_secrets_json)
    with open('token.pickle', 'wb') as f: f.write(base64.b64decode(token_b64))
    
    with open('token.pickle', 'rb') as f: creds = pickle.load(f)
    return build("youtube", "v3", credentials=creds)

# ... (Include your existing upload_to_youtube and run_automation functions here) ...
# Ensure you set headless=True in the browser launch for GitHub