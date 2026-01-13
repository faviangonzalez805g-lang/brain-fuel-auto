import os
import random
import re
import textwrap
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

# Captions area
TOP_MARGIN = 220
SIDE_MARGIN = 90
CAPTION_BOX_W = WIDTH - 2 * SIDE_MARGIN
BRAND_BAR_H = 150

# Branding
BRAND_TEXT_1 = "YouTube: Brain Fuel Media"
BRAND_TEXT_2 = "IG/TikTok: @Brain.FuelMedia"

# Style
BG_DARKEN_ALPHA = 120  # 0-255. higher = darker overlay behind text
WHITE = (255, 255, 255, 255)
YELLOW = (255, 225, 0, 255)

# Voice
TARGET_SECONDS = 58          # 55-60 is best for Shorts
VOICE_SPEED = 1.18           # >1 = faster (1.12–1.25 sweet spot)
# -----------------------------------------


def download_bg_video():
    """
    Downloads a vertical background video clip.
    If it fails, we fall back to solid background.
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


def build_script_to_target():
    """
    Builds a ~60s script using short, punchy sentences (better retention).
    """
    lines = [
        "Psychology says your brain treats uncertainty like danger.",
        "When you don’t know what’s next, your stress system turns on automatically.",
        "That’s why routines reduce anxiety fast — they make life predictable.",
        "Predictability tells your brain: you’re safe.",
        "Here’s the trick: don’t build discipline. Build structure.",
        "Put the habit where it’s easy to start, and remove the friction.",
        "Make the first step tiny… like two minutes.",
        "Your brain only needs a small win to keep going.",
        "And if you miss a day, don’t restart. Just return.",
        "Consistency beats intensity every time.",
        "Follow Brain Fuel Media for daily psychology that actually helps."
    ]
    # We'll just join these. If it ends up short after speed-up, we can add more lines.
    return " ".join(lines)


def split_sentences(text: str):
    # Split into sentences for highlighting
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def fit_font(draw, text, max_w, max_h, start=72, min_size=34):
    size = start
    while size >= min_size:
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=10, align="center")
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_w and h <= max_h:
            return font
        size -= 2
    return ImageFont.truetype(FONT_PATH, min_size)


def make_caption_png(full_text, highlight_sentence=None):
    """
    Renders full_text in white.
    If highlight_sentence is provided, that sentence is drawn again in yellow on top.
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark overlay behind captions for readability
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(0, 0, 0, 0))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Caption box height (exclude brand bar)
    caption_box_h = HEIGHT - TOP_MARGIN - BRAND_BAR_H - 120

    wrapped = textwrap.fill(full_text, width=34)

    font = fit_font(draw, wrapped, CAPTION_BOX_W, caption_box_h, start=68, min_size=34)

    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, align="center")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    y = TOP_MARGIN + (caption_box_h - th) // 2

    # shadow
    draw.multiline_text((x+3, y+3), wrapped, font=font, fill=(0, 0, 0, 180), spacing=10, align="center")
    # main white
    draw.multiline_text((x, y), wrapped, font=font, fill=WHITE, spacing=10, align="center")

    # Highlight sentence (overlay in yellow)
    if highlight_sentence:
        # Make a wrapped version of highlight_sentence so it aligns
        hs = highlight_sentence.strip()
        # find where it appears in the full wrapped text
        # (Simple approach: draw yellow sentence centered as its own block—works well visually)
        hs_wrapped = textwrap.fill(hs, width=34)
        hs_bbox = draw.multiline_textbbox((0, 0), hs_wrapped, font=font, spacing=10, align="center")
        hsw = hs_bbox[2] - hs_bbox[0]
        hsh = hs_bbox[3] - hs_bbox[1]
        hx = (WIDTH - hsw) // 2
        # Put highlight near middle (same area); not perfect word-level but reads like “active line”
        hy = y
        draw.multiline_text((hx, hy), hs_wrapped, font=font, fill=YELLOW, spacing=10, align="center")

    out = "captions.png"
    img.save(out)
    return out


def make_brand_png():
    """
    Two-line branding so it never cuts off.
    """
    w, h = WIDTH, BRAND_BAR_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue bar
    draw.rectangle([0, 0, w, h], fill=(20, 120, 255, 255))

    font = ImageFont.truetype(FONT_PATH, 34)

    # line 1
    b1 = BRAND_TEXT_1
    b1_bbox = draw.textbbox((0, 0), b1, font=font)
    b1_w_
