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
    # fallback solid background
    bg = ColorClip(size=(WIDTH, HEIGHT), color=(10, 10, 10), duration=duration)

# 3) Build readable captions image (no cut-off)
wrapped = textwrap.fill(SCRIPT, width=MAX_TEXT_WIDTH_CHARS)

img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Caption area excludes branding bar
caption_box_w = WIDTH - 2 * SIDE_MARGIN
caption_box_h = HEIGHT - TOP_MARGIN - BRAND_BAR_H - 120

font = fit_text(
    draw,
    wrapped,
    FONT_PATH,
    max_width_px=caption_box_w,
    max_height_px=caption_box_h,
    start_size=72,
    min_size=34
)

# Add a subtle shadow + stroke effect for readability
bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, align="center")
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]

x = (WIDTH - text_w) // 2
y = TOP_MARGIN + (caption_box_h - text_h) // 2

# Shadow
draw.multiline_text((x+3, y+3), wrapped, font=font, fill=(0, 0, 0, 180), spacing=10, align="center")
# Main text
draw.multiline_text((x, y), wrapped, font=font, fill=(255, 255, 255, 255), spacing=10, align="center")

img.save("captions.png")
captions_clip = ImageClip("captions.png").set_duration(duration)

# 4) Branding bar with color
bar = ColorClip(size=(WIDTH, BRAND_BAR_H), color=(20, 120, 255), duration=duration)  # blue bar
bar = bar.set_position((0, HEIGHT - BRAND_BAR_H))

# Branding text on top of bar
brand_img = Image.new("RGBA", (WIDTH, BRAND_BAR_H), (0, 0, 0, 0))
brand_draw = ImageDraw.Draw(brand_img)
brand_font = ImageFont.truetype(FONT_PATH, 34)

bt_bbox = brand_draw.textbbox((0, 0), BRAND_TEXT, font=brand_font)
bt_w = bt_bbox[2] - bt_bbox[0]
bt_h = bt_bbox[3] - bt_bbox[1]
bt_x = (WIDTH - bt_w) // 2
bt_y = (BRAND_BAR_H - bt_h) // 2

# slight shadow
brand_draw.text((bt_x+2, bt_y+2), BRAND_TEXT, font=brand_font, fill=(0, 0, 0, 140))
brand_draw.text((bt_x, bt_y), BRAND_TEXT, font=brand_font, fill=(255, 255, 255, 255))

brand_img.save("brand.png")
brand_text_clip = ImageClip("brand.png").set_duration(duration).set_position((0, HEIGHT - BRAND_BAR_H))

# 5) Composite + audio
final = CompositeVideoClip([bg, captions_clip, bar, brand_text_clip]).set_audio(audio)

final.write_videofile(
    OUTPUT_VIDEO,
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print("✅ Video generated:", OUTPUT_VIDEO, "duration:", duration)
