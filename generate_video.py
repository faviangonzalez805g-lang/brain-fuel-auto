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

MIN_DURATION = 60  # NEVER less than 60s
VOICE_SPEED = 1.1  # slightly faster speech

SCRIPT = (
    "Psychology says your brain avoids uncertainty because it feels unsafe. "
    "When you don’t know what’s next, your stress system turns on automatically. "
    "That’s why routines reduce anxiety fast. Predictability tells your brain you’re safe. "
    "Here’s the trick. You don’t build discipline. You build structure. "
    "Make the habit easy to start and remove friction. "
    "Start small. Even two minutes counts. "
    "Your brain only needs one small win to keep going. "
    "If you miss a day, don’t restart. Just return. "
    "Consistency beats intensity every time. "
    "Follow Brain Fuel Media for daily psychology that actually helps."
)

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG / TikTok: @Brain.FuelMedia"
# ===================================================


# ---------- 1. Generate Voice ----------
tts = gTTS(SCRIPT, slow=False)
tts.save("voice_raw.mp3")

voice = AudioFileClip("voice_raw.mp3").fx(vfx.speedx, VOICE_SPEED)

# Force minimum duration
duration = max(MIN_DURATION, voice.duration)


# ---------- 2. Animated Background (GUARANTEED) ----------
background = (
    ColorClip(size=(WIDTH, HEIGHT), color=(12, 12, 12), duration=duration)
    .fx(vfx.resize, lambda t: 1.02 + 0.02 * (t / duration))
    .set_position("center")
)


# ---------- 3. Caption Image ----------
img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(FONT_PATH, MAIN_FONT_SIZE)
brand_font = ImageFont.truetype(FONT_PATH, BRAND_FONT_SIZE)

wrapped = textwrap.fill(SCRIPT, width=36)

bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]

# Lower center placement
text_x = (WIDTH - text_w) // 2
text_y = int(HEIGHT * 0.42)

draw.multiline_text(
    (text_x, text_y),
    wrapped,
    font=font,
    fill="#FFD700",  # yellow
    align="center"
)

# ---------- 4. Branding Bar ----------
bar_height = 120
bar = Image.new("RGBA", (WIDTH, bar_height), (0, 90, 180, 255))
img.paste(bar, (0, HEIGHT - bar_height))

brand_bbox = draw.textbbox((0, 0), BRAND_TEXT, font=brand_font)
brand_w = brand_bbox[2] - brand_bbox[0]

draw.text(
    ((WIDTH - brand_w) // 2, HEIGHT - bar_height + 35),
    BRAND_TEXT,
    font=brand_font,
    fill="white"
)

img.save("captions.png")


# ---------- 5. Build Video ----------
captions_clip = ImageClip("captions.png").set_duration(duration)

final = (
    CompositeVideoClip([background, captions_clip])
    .set_audio(voice)
    .set_duration(duration)
)

final.write_videofile(
    "brain_fuel_test.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print("✅ Video rendered successfully (60s+)")
