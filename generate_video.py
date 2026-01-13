import os
import subprocess
import textwrap
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    CompositeVideoClip,
    ColorClip,
    AudioFileClip,
    ImageClip,
    vfx
)

# ===================== SETTINGS =====================
WIDTH, HEIGHT = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

MAIN_FONT_SIZE = 64
BRAND_FONT_SIZE = 40

TARGET_SECONDS = 62
VOICE_SPEED = 1.12

SCRIPT = (
    "Your brain treats uncertainty like danger. "
    "When you don’t know what’s next, stress turns on automatically. "
    "Routines reduce anxiety fast because life feels predictable. "
    "Predictability tells your brain you’re safe. "
    "Don’t build discipline. Build structure. "
    "Make the first step tiny… like two minutes. "
    "Small wins create momentum. "
    "If you miss a day, don’t restart — just return. "
    "Consistency beats intensity every time. "
    "Put reminders in your environment, not in your memory. "
    "Follow Brain Fuel Media for daily mind shifts."
)

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"

RAW_OUT = "brain_fuel_test.mp4"
FINAL_OUT = "brain_fuel_final.mp4"
# ===================================================


def sh(cmd_list):
    subprocess.run(cmd_list, check=True)


# ---------- 1) Voice ----------
gTTS(SCRIPT, slow=False).save("voice_raw.mp3")

# Speed up
sh(["ffmpeg", "-y", "-i", "voice_raw.mp3", "-filter:a", f"atempo={VOICE_SPEED}", "voice_fast.mp3"])

# Pad/truncate to EXACT duration
sh(["ffmpeg", "-y", "-i", "voice_fast.mp3", "-af", f"apad=pad_dur={TARGET_SECONDS}", "-t", str(TARGET_SECONDS), "voice.mp3"])

voice = AudioFileClip("voice.mp3").set_duration(TARGET_SECONDS)
duration = TARGET_SECONDS


# ---------- 2) Background (guaranteed visuals) ----------
background = (
    ColorClip(size=(WIDTH, HEIGHT), color=(12, 12, 12), duration=duration)
    .fx(vfx.resize, lambda t: 1.02 + 0.02 * (t / duration))
    .set_position("center")
)
overlay = ColorClip(size=(WIDTH, HEIGHT), color=(0, 90, 180), duration=duration).set_opacity(0.10)


# ---------- 3) Captions image ----------
img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(FONT_PATH, MAIN_FONT_SIZE)
brand_font = ImageFont.truetype(FONT_PATH, BRAND_FONT_SIZE)

wrapped = textwrap.fill(SCRIPT, width=36)

bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, align="center")
text_w = bbox[2] - bbox[0]
text_x = (WIDTH - text_w) // 2
text_y = int(HEIGHT * 0.40)

# shadow + yellow
draw.multiline_text((text_x + 3, text_y + 3), wrapped, font=font, fill=(0, 0, 0, 190), spacing=10, align="center")
draw.multiline_text((text_x, text_y), wrapped, font=font, fill=(255, 225, 0, 255), spacing=10, align="center")

# brand bar
bar_h = 120
bar = Image.new("RGBA", (WIDTH, bar_h), (20, 120, 255, 255))
img.paste(bar, (0, HEIGHT - bar_h))

brand_bbox = draw.textbbox((0, 0), BRAND_TEXT, font=brand_font)
brand_w = brand_bbox[2] - brand_bbox[0]
brand_x = (WIDTH - brand_w) // 2
brand_y = HEIGHT - bar_h + 35

draw.text((brand_x + 2, brand_y + 2), BRAND_TEXT, font=brand_font, fill=(0, 0, 0, 140))
draw.text((brand_x, brand_y), BRAND_TEXT, font=brand_font, fill=(255, 255, 255, 255))

img.save("captions.png")
captions_clip = ImageClip("captions.png").set_duration(duration)


# ---------- 4) Compose ----------
final = CompositeVideoClip([background, overlay, captions_clip]).set_audio(voice).set_duration(duration)

final.write_videofile(
    RAW_OUT,
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

# ---------- 5) Re-encode for MAX compatibility (Windows/iPhone) ----------
# Baseline profile plays on basically everything.
# yuv420p is required for many players.
sh([
    "ffmpeg", "-y", "-i", RAW_OUT,
    "-r", "30",
    "-c:v", "libx264",
    "-profile:v", "baseline",
    "-level", "3.0",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "-c:a", "aac",
    "-b:a", "192k",
    "-ar", "44100",
    "-ac", "2",
    FINAL_OUT
])

# Sanity check file exists and has size
size = os.path.getsize(FINAL_OUT)
print("✅ FINAL MP4:", FINAL_OUT, "bytes:", size)
if size < 100000:  # <100KB is basically broken
    raise RuntimeError("Final video file is too small / likely corrupted.")
