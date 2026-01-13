import os, math, textwrap
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    CompositeVideoClip, AudioFileClip, ImageClip, VideoClip, vfx
)

# ===================== SETTINGS =====================
WIDTH, HEIGHT = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TARGET_SECONDS = 62        # 60+ seconds
VOICE_SPEED = 1.15         # faster speech
FPS = 30

SCRIPT = (
    "Your brain treats uncertainty like danger. "
    "When you don’t know what’s next, stress turns on automatically. "
    "Routines reduce anxiety fast because they make life predictable. "
    "Predictability tells your brain: you’re safe. "
    "Here’s the trick: don’t build discipline — build structure. "
    "Make the first step tiny… even two minutes counts. "
    "Small wins create momentum. "
    "If you miss a day, don’t restart — just return. "
    "Consistency beats intensity every time. "
    "Put reminders in your environment, not in your memory. "
    "Follow Brain Fuel Media for daily mind shifts."
)

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"
OUTFILE = "brain_fuel_final.mp4"
# ===================================================

def sh(cmd: str):
    # quiet shell command
    os.system(cmd + " >/dev/null 2>&1")

# ---------- 1) VOICE ----------
gTTS(SCRIPT, slow=False).save("voice_raw.mp3")

# Speed up voice
sh(f'ffmpeg -y -i voice_raw.mp3 -filter:a "atempo={VOICE_SPEED}" voice_fast.mp3')

# Loop voice to full duration so it keeps talking (no silence)
# Try stream-copy first (fast)
sh(f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} -c copy voice_loop.mp3')

# If stream-copy fails, re-encode
if (not os.path.exists("voice_loop.mp3")) or os.path.getsize("voice_loop.mp3") < 10000:
    sh(
        f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} '
        f'-c:a libmp3lame -q:a 4 voice_loop.mp3'
    )

voice = AudioFileClip("voice_loop.mp3").set_duration(TARGET_SECONDS)

# ---------- 2) BACKGROUND VISUALS (NEON WAVES, FREE) ----------
def make_bg_frame(t):
    h, w = HEIGHT, WIDTH

    # full grids (H,W)
    yy = np.linspace(0, 1, h).reshape(h, 1)
    xx = np.linspace(0, 1, w).reshape(1, w)
    Y = np.repeat(yy, w, axis=1)
    X = np.repeat(xx, h, axis=0)

    # base dark gradient
    base = 12 + 18 * (1 - Y)

    # moving neon waves
    wave1 = 70 * (np.sin(2 * math.pi * (X * 1.2 + t * 0.05)) * 0.5 + 0.5)
    wave2 = 55 * (np.sin(2 * math.pi * (Y * 1.6 - t * 0.06)) * 0.5 + 0.5)

    # RGB channels
    r = base + 0.25 * wave2
    g = base + 0.55 * wave1
    b = base + 1.15 * wave1 + 0.55 * wave2

    frame = np.clip(np.dstack([r, g, b]), 0, 255).astype(np.uint8)
    return frame

bg = VideoClip(make_bg_frame, duration=TARGET_SECONDS).set_fps(FPS)

# ---------- 3) TEXT (FIT + NO OFFSCREEN) ----------
font = ImageFont.truetype(FONT_PATH, 54)      # smaller so it fits
draw_test = ImageDraw.Draw(Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)))

MARGIN_X = 80
TOP_Y = int(HEIGHT * 0.24)                    # text a bit lower like you asked
MAX_TEXT_WIDTH = WIDTH - (MARGIN_X * 2)

def wrap_to_width(draw, text, font, max_width):
    words = text.split()
    lines = []
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return "\n".join(lines)

wrapped = wrap_to_width(draw_test, SCRIPT, font, MAX_TEXT_WIDTH)

# Create caption overlay image
img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=14, align="center")
tw = bbox[2] - bbox[0]
tx = (WIDTH - tw) // 2
ty = TOP_Y

# shadow
draw.multiline_text(
    (tx + 3, ty + 3),
    wrapped,
    font=font,
    fill=(0, 0, 0, 180),
    spacing=14,
    align="center"
)

# yellow main text
draw.multiline_text(
    (tx, ty),
    wrapped,
    font=font,
    fill=(255, 220, 0, 255),
    spacing=14,
    align="center"
)

# ---------- 4) BRAND BAR (AUTO-FIT, NO CUT OFF) ----------
bar_h = 120
bar_color = (10, 90, 200, 230)
bar = Image.new("RGBA", (WIDTH, bar_h), bar_color)
img.paste(bar, (0, HEIGHT - bar_h))

# start bigger then shrink until fits
bf_size = 34
while True:
    brand_font = ImageFont.truetype(FONT_PATH, bf_size)
    bw = draw.textlength(BRAND_TEXT, font=brand_font)
    if bw <= WIDTH - 60 or bf_size <= 22:
        break
    bf_size -= 1

bx = int((WIDTH - bw) // 2)
by = HEIGHT - bar_h + 38

draw.text((bx + 2, by + 2), BRAND_TEXT, font=brand_font, fill=(0, 0, 0, 140))
draw.text((bx, by), BRAND_TEXT, font=brand_font, fill=(255, 255, 255, 255))

img.save("captions.png")
captions = ImageClip("captions.png").set_duration(TARGET_SECONDS)

# ---------- 5) COMPOSE + EXPORT ----------
final = CompositeVideoClip([bg, captions], size=(WIDTH, HEIGHT)).set_audio(voice)
final = final.fx(vfx.resize, newsize=(WIDTH, HEIGHT))  # keep exact even size

final.write_videofile(
    OUTFILE,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    audio_fps=44100,
    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]
)

print("✅ Video created:", OUTFILE)
