import os, math, random, re, glob
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    CompositeVideoClip, AudioFileClip, ImageClip, VideoClip, VideoFileClip, concatenate_videoclips
)

# ===================== SETTINGS =====================
WIDTH, HEIGHT = 1080, 1920
FPS = 30
TARGET_SECONDS = 62
VOICE_SPEED = 1.18  # faster voice

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HOOK = "Your brain hates this one thing… and it’s why you feel stressed."
MAIN = (
    "Uncertainty feels like danger to your brain. "
    "When you don’t know what’s next, stress turns on automatically. "
    "That’s why routines reduce anxiety fast: they make life predictable. "
    "Predictability tells your brain, you’re safe. "
    "Here’s the trick: don’t build discipline — build structure. "
    "Make the first step tiny… even two minutes counts. "
    "Small wins create momentum. "
    "If you miss a day, don’t restart — just return. "
    "Consistency beats intensity every time. "
    "Put reminders in your environment, not in your memory."
)
CTA = "Follow Brain Fuel Media for daily mind shifts."
SCRIPT = f"{HOOK} {MAIN} {CTA}"

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"
OUTFILE = "brain_fuel_final.mp4"

# ==== ElevenLabs controls (SAFE TESTING) ====
DRY_RUN_ELEVENLABS = True  # ✅ keep True while testing visuals/captions
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")  # set later
# ===================================================


def sh(cmd: str):
    os.system(cmd + " >/dev/null 2>&1")


def ensure_file(path: str):
    return os.path.exists(path) and os.path.getsize(path) > 10000


def paste_rgba_safe(base, overlay, pos):
    base = base.convert("RGBA")
    overlay = overlay.convert("RGBA")
    tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tmp.paste(overlay, pos)
    return Image.alpha_composite(base, tmp)


# ---------- 1) AUDIO ----------
# A) Safe testing mode: gTTS (free)
if DRY_RUN_ELEVENLABS or not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
    gTTS(SCRIPT, slow=False).save("voice_raw.mp3")
else:
    # B) ElevenLabs mode (only when you flip DRY_RUN_ELEVENLABS=False)
    # Minimal dependency approach: use curl so no extra pip packages needed
    # Saves to voice_raw.mp3
    safe_text = SCRIPT.replace('"', '\\"')
    sh(
        f'curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}" '
        f'-H "xi-api-key: {ELEVEN_API_KEY}" '
        f'-H "Content-Type: application/json" '
        f'-d "{{\\"text\\":\\"{safe_text}\\",\\"model_id\\":\\"eleven_multilingual_v2\\",'
        f'\\"voice_settings\\":{{\\"stability\\":0.4,\\"similarity_boost\\":0.85}}}}" '
        f'--output voice_raw.mp3'
    )

# speed + loudness normalize
sh(
    f'ffmpeg -y -i voice_raw.mp3 '
    f'-filter:a "atempo={VOICE_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11" '
    f'voice_fast.mp3'
)

# loop voice to full length
sh(f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} -c copy voice_loop.mp3')
if not ensure_file("voice_loop.mp3"):
    sh(
        f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} '
        f'-c:a libmp3lame -q:a 4 voice_loop.mp3'
    )

voice = AudioFileClip("voice_loop.mp3").set_duration(TARGET_SECONDS)

# ---------- 2) WORD TIMING ----------
def clean_words(text):
    text = re.sub(r"[^a-zA-Z0-9'’\s]", "", text)
    return [w for w in text.split() if w.strip()]

WORDS = clean_words(SCRIPT)
audio_dur = max(1.0, min(voice.duration, TARGET_SECONDS))
wps = max(1.9, len(WORDS) / audio_dur)

word_times = []
tcur = 0.0
for w in WORDS:
    base = 1.0 / wps
    bonus = min(0.08, max(0.0, (len(w) - 6) * 0.01))
    dt = base + bonus
    word_times.append((tcur, min(tcur + dt, TARGET_SECONDS), w))
    tcur += dt
word_times = [(s, e, w) for (s, e, w) in word_times if s < TARGET_SECONDS]

# ---------- 3) BACKGROUND: MOTION LOOPS ----------
def build_loop_background():
    loop_paths = sorted(glob.glob("assets/loops/*.mp4"))
    if not loop_paths:
        raise SystemExit(
            "❌ No motion loops found. Add MP4 files to: assets/loops/"
        )

    # Load & prep clips
    clips = []
    for p in loop_paths:
        c = VideoFileClip(p, audio=False)
        c = c.resize((WIDTH, HEIGHT)).set_fps(FPS)
        clips.append(c)

    # Randomize order each run
    random.shuffle(clips)

    # Repeat until we cover duration
    built = []
    total = 0.0
    idx = 0
    while total < TARGET_SECONDS:
        c = clips[idx % len(clips)]
        built.append(c)
        total += c.duration
        idx += 1

    bg = concatenate_videoclips(built, method="compose")
    bg = bg.subclip(0, TARGET_SECONDS)
    return bg

bg = build_loop_background()

# ---------- 4) CAPTIONS ----------
FONT_MAIN = ImageFont.truetype(FONT_PATH, 70
