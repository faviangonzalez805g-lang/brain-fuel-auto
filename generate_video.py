import os
import random
import textwrap
import urllib.request

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    ColorClip
)

# ---------------- SETTINGS ----------------
SCRIPT = (
    "Psychology says your brain avoids uncertainty because it feels unsafe. "
    "That is why routines reduce stress so fast. "
    "When your brain knows what comes next, it conserves energy. "
    "That is why structure improves focus and emotional control. "
    "Follow Brain Fuel Media for daily psychology that actually helps."
)

WIDTH, HEIGHT = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Text layout
MAX_TEXT_WIDTH_CHARS = 28     # tighter wrap so it doesn't run off screen
TOP_MARGIN = 220
SIDE_MARGIN = 90

# Branding bar
BRAND_BAR_H = 140
BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"

OUTPUT_VIDEO = "brain_fuel_test.mp4"
# -----------------------------------------


def download_bg_video():
    """
    Downloads a free vertical background video (public domain / Pexels CDN).
    If it fails, we fall back to a solid background.
    """
    url_options = [
        # These links can change over time; if one breaks, add another.
        "https://videos.pexels.com/video-files/3195394/3195394-uhd_1440_2560_25fps.mp4",
        "https://videos.pexels.com/video-files/854418/854418-hd_1080_1920_30fps.mp4",
        "https://videos.pexels.com/video-files/2795748/2795748-hd_1080_1920_30fps.mp4",
    ]
    url = random.choice(url_options)
    out = "bg.mp4"
    try:
        urllib.request.urlretrieve(url, out)
        return out
    except Exception:
        return None


def fit_text(draw, text, font_path, max_width_px, max_height_px, start_size=72, min_size=34):
    """
    Finds the largest font size that fits inside the given box.
    """
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=10, align="center")
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_width_px and h <= max_height_px:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


# 1) Voice
tts = gTTS(SCRIPT)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
duration = audio.duration  # ✅ match video length to voice

# 2) Background video (real)
bg_path = download_bg_video()

if bg_path and os.path.exists(bg_path):
    bg = VideoFileClip(bg_path).subclip(0, min(duration, VideoFileClip(bg_path).duration))
    bg = bg.resize(height=HEIGHT)
    # center-crop to width
    if bg.w > WIDTH:
        x1 = (bg.w - WIDTH) // 2
        bg = bg.crop(x1=x1, y1=0, x2=x1 + WIDTH, y2=HEIGHT)
    else:
        bg = bg.resize((WIDTH, HEIGHT))
    bg = bg.set_duration(duration)
else:
    # fallback solid
