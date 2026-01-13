import os
import random
import re
import urllib.request
from pathlib import Path

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    ColorClip,
    concatenate_videoclips
)

# ---------------- SETTINGS ----------------
WIDTH, HEIGHT = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Make sure final video is NEVER under 60s
TARGET_SECONDS = 62

# Captions placement (lower = bigger y)
CAPTION_Y_START = 420   # move text lower (try 420–520)
SIDE_MARGIN = 90
CAPTION_MAX_W = WIDTH - 2 * SIDE_MARGIN

# Caption style
FONT_SIZE = 74          # big + readable
LINE_SPACING = 14
STROKE_W = 6            # bold outline
SHADOW_OFFSET = 4

# Brand bar
BRAND_BAR_H = 150
BRAND_TEXT_1 = "YouTube: Brain Fuel Media"
BRAND_TEXT_2 = "IG/TikTok: @Brain.FuelMedia"

# Colors
WHITE = (255, 255, 255, 255)
YELLOW = (255, 225, 0, 255)
RED = (255, 60, 60, 255)
GREEN = (80, 255, 120, 255)

# Voice
VOICE_SPEED = 1.18  # faster voice (1.12–1.25 sweet spot)
# -----------------------------------------


def download_bg_video():
    """
    Download a vertical background video and loop it.
    """
    url_options = [
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


def build_script():
    """
    Short, punchy lines. This is what we highlight line-by-line.
    """
    lines = [
        "Your brain treats uncertainty like danger.",
        "When you don’t know what’s next, stress turns on automatically.",
        "Routines reduce anxiety fast because life feels predictable.",
        "Predictability tells your brain: you’re safe.",
        "Don’t build discipline. Build structure.",
        "Make the first step tiny… like two minutes.",
        "Small wins create momentum.",
        "If you miss a day, don’t restart — just return.",
        "Consistency beats intensity every time.",
        "Put reminders in your environment, not in your memory.",
        "Follow Brain Fuel Media for daily mind shifts."
    ]
    return lines


def split_into_lines_for_caption(text, font, draw):
    """
    Wraps a single line so it fits the screen width.
    """
    words = text.split()
    lines = []
    cur = []
    for w in words:
        test = " ".join(cur + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= CAPTION_MAX_W:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def color_word(word):
    """
    Simple color rules:
    - Red for punch/aggressive words
    - Green for action/positive
    - Yellow default
    """
    w = re.sub(r"[^\w’']", "", word.lower())

    red_words = {"danger", "stress", "anxiety", "unsafe", "restart", "intensity"}
    green_words = {"safe", "structure", "tiny", "two", "minutes", "momentum", "return", "consistency", "wins"}

    if w in red_words:
        return RED
    if w in green_words:
        return GREEN
    return YELLOW


def draw_text_with_outline(draw, xy, text, font, fill):
    """
    Bold/outlined text for readability.
    """
    x, y = xy
    # Outline (stroke)
    for dx in range(-STROKE_W, STROKE_W + 1):
        for dy in range(-STROKE_W, STROKE_W + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 220))
    # Shadow
    draw.text((x + SHADOW_OFFSET, y + SHADOW_OFFSET), text, font=font, fill=(0, 0, 0, 180))
    # Main
    draw.text((x, y), text, font=font, fill=fill)


def make_caption_frame(current_line):
    """
    Creates ONE frame image for the current caption line(s).
    Only shows the current line (no full white script at all).
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Wrap the line if it’s long (can become 1–3 lines)
    wrapped_lines = split_into_lines_for_caption(current_line, font, draw)

    # Compute total block height
    line_heights = []
    max_w = 0
    for ln in wrapped_lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_w = max(max_w, w)
        line_heights.append(h)

    block_h = sum(line_heights) + LINE_SPACING * (len(wrapped_lines) - 1)

    # Place centered horizontally, and lower vertically
    start_y = CAPTION_Y_START + max(0, (520 - block_h) // 2)

    y = start_y
    for idx, ln in enumerate(wrapped_lines):
        # Word-by-word color on the same line
        words = ln.split(" ")
        # measure total width of colored word layout
        widths = []
        for w in words:
            bbox = draw.textbbox((0, 0), w, font=font)
            widths.append(bbox[2] - bbox[0])
        space_w = draw.textbbox((0, 0), " ", font=font)[2]
        total_w = sum(widths) + space_w * (len(words) - 1)
        x = (WIDTH - total_w) // 2

        for i, w in enumerate(words):
            fill = color_word(w)
            draw_text_with_outline(draw, (x, y), w, font, fill)
            x += widths[i] + space_w

        y += line_heights[idx] + LINE_SPACING

    out = "caption.png"
    img.save(out)
    return out


def make_brand_png():
    """
    Two-line brand bar so text never cuts off.
    """
    w, h = WIDTH, BRAND_BAR_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue bar
    draw.rectangle([0, 0, w, h], fill=(20, 120, 255, 255))

    font = ImageFont.truetype(FONT_PATH, 34)

    def center_line(text, y):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 140))
        draw.text((x, y), text, font=font, fill=WHITE)

    center_line(BRAND_TEXT_1, 22)
    center_line(BRAND_TEXT_2, 82)

    out = "brand.png"
    img.save(out)
    return out


# ----------------- MAIN -----------------
lines = build_script()

# Build a longer script for voice by joining lines + a few extras
voice_script = " ".join(lines + [
    "Here’s your reminder: make it easy to start.",
    "Your brain loves progress more than perfection.",
    "Follow Brain Fuel Media for daily psychology that actually helps."
])

# TTS
gTTS(voice_script).save("voice_raw.mp3")

# Speed up with ffmpeg
os.system(f'ffmpeg -y -i voice_raw.mp3 -filter:a "atempo={VOICE_SPEED}" voice.mp3 >/dev/null 2>&1')
audio = AudioFileClip("voice.mp3")

# Force >= 60s by looping/holding audio if needed:
# If audio is short, we just extend video with the last audio frame (silence isn’t ideal but works).
duration = max(TARGET_SECONDS, audio.duration)

# Background video + loop to duration
bg_path = download_bg_video()

if bg_path and Path(bg_path).exists():
    raw = VideoFileClip(bg_path)
    raw = raw.resize(height=HEIGHT)
    if raw.w > WIDTH:
        x1 = (raw.w - WIDTH) // 2
        raw = raw.crop(x1=x1, y1=0, x2=x1 + WIDTH, y2=HEIGHT)
    else:
        raw = raw.resize((WIDTH, HEIGHT))

    clips = []
    t = 0
    while t < duration:
        seg = raw.subclip(0, min(raw.duration, duration - t))
        clips.append(seg)
        t += seg.duration
    bg = concatenate_videoclips(clips).set_duration(duration)
else:
    # Fallback: subtle moving overlay so it isn't "dead"
    bg = ColorClip(size=(WIDTH, HEIGHT), color=(10, 10, 10), duration=duration)

# Dark overlay for readability
dark = ColorClip(size=(WIDTH, HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0.35)

# Captions: show ONE line at a time
per_line = duration / max(len(lines), 1)
caption_clips = []

for i, line in enumerate(lines):
    start = i * per_line
    end = min((i + 1) * per_line, duration)
    png = make_caption_frame(line)
    caption_clips.append(ImageClip(png).set_start(start).set_end(end))

# Brand bar
brand_png = make_brand_png()
brand_clip = ImageClip(brand_png).set_duration(duration).set_position((0, HEIGHT - BRAND_BAR_H))

final = CompositeVideoClip([bg, dark, *caption_clips, brand_clip]).set_audio(audio).set_duration(duration)

final.write_videofile(
    "brain_fuel_test.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print("✅ Video generated:", "brain_fuel_test.mp4", "duration:", duration)
