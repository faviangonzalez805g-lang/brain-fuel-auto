import os
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

DURATION = 62
VOICE_SPEED = 1.12

SCRIPT = (
    "Your brain treats uncertainty like danger. "
    "When you don’t know what’s next, stress turns on automatically. "
    "Routines reduce anxiety fast because life feels predictable. "
    "Predictability tells your brain you’re safe. "
    "Don’t build discipline. Build structure. "
    "Make the first step tiny. Even two minutes counts. "
    "Small wins create momentum. "
    "If you miss a day, don’t restart. Just return. "
    "Consistency beats intensity every time. "
    "Follow Brain Fuel Media for daily mind shifts."
)

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"
OUTPUT = "brain_fuel_final.mp4"
# ===================================================


# ---------- 1) Voice ----------
gTTS(SCRIPT, slow=False).save("voice_raw.mp3")

os.system(
    f'ffmpeg -y -i voice_raw.mp3 '
    f'-filter:a "atempo={VOICE_SPEED},apad=pad_dur={DURATION}" '
    f'-t {DURATION} voice.mp3 >/dev/null 2>&1'
)

voice = AudioFileClip("voice.mp3").set_duration(DURATION)


# ---------- 2) Background ----------
background = (
    ColorClip((WIDTH, HEIGHT), color=(12, 12, 12), duration=DURATION)
    .fx(vfx.resize, lambda t: 1.02 + 0.02 * (t / DURATION))
)

overlay = ColorClip((WIDTH, HEIGHT), color=(0, 100, 200), duration=DURATION).set_opacity(0.12)


# ---------- 3) Captions ----------
img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(FONT_PATH, MAIN_FONT_SIZE)
brand_font = ImageFont.truetype(FONT_PATH, BRAND_FONT_SIZE)

wrapped = textwrap.fill(SCRIPT, width=36)

bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, align="center")
text_w = bbox[2] - bbox[0]
text_x = (WIDTH - text_w) // 2
text_y = int(HEIGHT * 0.40)

# shadow
draw.multiline_text(
    (text_x + 3, text_y + 3),
    wrapped,
    font=font,
    fill=(0, 0, 0, 200),
    spacing=10,
    align="center"
)

# yellow
draw.multiline_text(
    (text_x, text_y),
    wrapped,
    font=font,
    fill=(255, 220, 0, 255),
    spacing=10,
    align="center"
)

# Branding bar
bar_h = 120
bar = Image.new("RGBA", (WIDTH, bar_h), (25, 120, 255, 255))
img.paste(bar, (0, HEIGHT - bar_h))

brand_bbox = draw.textbbox((0, 0), BRAND_TEXT, font=brand_font)
brand_w = brand_bbox[2] - brand_bbox[0]
brand_x = (WIDTH - brand_w) // 2
brand_y = HEIGHT - bar_h + 36

draw.text((brand_x, brand_y), BRAND_TEXT, font=brand_font, fill="white")

img.save("captions.png")
captions = ImageClip("captions.png").set_duration(DURATION)


# ---------- 4) Final ----------
final = CompositeVideoClip([background, overlay, captions], size=(WIDTH, HEIGHT)).set_audio(voice)

# FORCE exact even dimensions (fixes libx264 width/height divisible-by-2 errors)
final = final.fx(vfx.resize, newsize=(WIDTH, HEIGHT))

final.write_videofile(
    OUTPUT,
    fps=30,
    codec="libx264",
    audio_codec="aac",
    audio_fps=44100,
    ffmpeg_params=[
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart"
    ]
)

print("✅ Video created:", OUTPUT)
