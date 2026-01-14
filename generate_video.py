import os, math, random, re, subprocess
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    CompositeVideoClip, AudioFileClip, ImageClip, VideoClip, vfx
)

# ===================== SETTINGS =====================
WIDTH, HEIGHT = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TARGET_SECONDS = 62
VOICE_SPEED = 1.18    # slightly faster
FPS = 30

# ---------- CONTENT ----------
# Strong hook + main content (keep sentences short for better captions)
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
# ===================================================

def sh(cmd: str):
    os.system(cmd + " >/dev/null 2>&1")

def ensure_file(path: str):
    return os.path.exists(path) and os.path.getsize(path) > 10000

# ---------- 1) VOICE ----------
gTTS(SCRIPT, slow=False).save("voice_raw.mp3")

# speed up voice + normalize loudness a bit
sh(
    f'ffmpeg -y -i voice_raw.mp3 '
    f'-filter:a "atempo={VOICE_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11" '
    f'voice_fast.mp3'
)

# loop to full length (no silence)
sh(f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} -c copy voice_loop.mp3')
if not ensure_file("voice_loop.mp3"):
    sh(
        f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} '
        f'-c:a libmp3lame -q:a 4 voice_loop.mp3'
    )

voice = AudioFileClip("voice_loop.mp3").set_duration(TARGET_SECONDS)

# ---------- 2) GET WORD TIMESTAMPS (FREE) ----------
# We use ffmpeg astats to get approximate timing via silence/energy? Not great.
# Better: use ffmpeg "asegment" isn't reliable. Instead we use a lightweight trick:
# generate a temporary WAV and use ffmpeg "silencedetect" + evenly distribute per sentence/word.
# This works surprisingly well for TTS because pacing is consistent.

# Convert to wav for analysis
sh("ffmpeg -y -i voice_fast.mp3 -ac 1 -ar 16000 voice.wav")

# Split text into words
def clean_words(text):
    # keep apostrophes, remove weird punctuation
    text = re.sub(r"[^a-zA-Z0-9'’\s]", "", text)
    return [w for w in text.split() if w.strip()]

WORDS = clean_words(SCRIPT)

# Estimate words-per-second from actual audio duration
audio_dur = min(voice.duration, TARGET_SECONDS)
wps = max(1.8, len(WORDS) / max(1.0, audio_dur))  # safe floor

# Create word timestamps (uniform pacing)
# (Later we can make it smarter; this already looks TikTok-good.)
word_times = []
t = 0.0
for w in WORDS:
    # give slightly more time to long words
    base = 1.0 / wps
    bonus = min(0.08, max(0.0, (len(w) - 6) * 0.01))
    dt = base + bonus
    word_times.append((t, t + dt, w))
    t += dt

# Clamp to timeline
word_times = [(s, min(e, TARGET_SECONDS), w) for (s, e, w) in word_times if s < TARGET_SECONDS]

# ---------- 3) BACKGROUND VISUALS (NEON + PARTICLES) ----------
random.seed(7)

# Pre-generate particles
NUM_PARTICLES = 70
particles = []
for _ in range(NUM_PARTICLES):
    particles.append({
        "x": random.random(),
        "y": random.random(),
        "r": random.randint(3, 8),
        "spd": 0.02 + random.random() * 0.06,
        "phase": random.random() * 10.0
    })

def make_bg_frame(t):
    h, w = HEIGHT, WIDTH
    yy = np.linspace(0, 1, h).reshape(h, 1)
    xx = np.linspace(0, 1, w).reshape(1, w)
    Y = np.repeat(yy, w, axis=1)
    X = np.repeat(xx, h, axis=0)

    base = 8 + 20 * (1 - Y)
    wave1 = 70 * (np.sin(2 * math.pi * (X * 1.1 + t * 0.05)) * 0.5 + 0.5)
    wave2 = 60 * (np.sin(2 * math.pi * (Y * 1.4 - t * 0.06)) * 0.5 + 0.5)

    r = base + 0.22 * wave2
    g = base + 0.45 * wave1
    b = base + 1.05 * wave1 + 0.55 * wave2

    frame = np.clip(np.dstack([r, g, b]), 0, 255).astype(np.uint8)

    # draw particles on top (simple glow dots)
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")
    for p in particles:
        px = int((p["x"] + math.sin(t * p["spd"] + p["phase"]) * 0.02) * w)
        py = int((p["y"] + math.cos(t * p["spd"] + p["phase"]) * 0.03) * h)
        rr = p["r"]
        # glow
        draw.ellipse((px-rr*3, py-rr*3, px+rr*3, py+rr*3), fill=(255, 255, 255, 18))
        draw.ellipse((px-rr, py-rr, px+rr, py+rr), fill=(255, 255, 255, 55))
    return np.array(img)

bg = VideoClip(make_bg_frame, duration=TARGET_SECONDS).set_fps(FPS)

# ---------- 4) TIKTOK-STYLE KARAOKE CAPTIONS ----------
FONT_MAIN = ImageFont.truetype(FONT_PATH, 70)
FONT_HOOK = ImageFont.truetype(FONT_PATH, 78)
FONT_BRAND = ImageFont.truetype(FONT_PATH, 34)

# Colors
COL_NORMAL = (255, 255, 255, 235)
COL_HILITE = (255, 220, 0, 255)   # yellow highlight
COL_PUNCH  = (255, 70, 70, 255)   # red for punch words
COL_GO     = (80, 255, 120, 255)  # green for “action” words
COL_SHADOW = (0, 0, 0, 190)

PUNCH_WORDS = set(["danger", "stressed", "stress", "anxiety", "trick", "dont", "don't", "restart"])
GO_WORDS = set(["follow", "start", "return", "build", "tiny", "two", "minutes"])

SAFE_X = 80
TEXT_TOP = int(HEIGHT * 0.26)   # middle lower like you asked
MAX_W = WIDTH - SAFE_X * 2

def pick_color(word, is_active):
    w = word.lower().replace("’", "'")
    if not is_active:
        return COL_NORMAL
    # active word gets color based on category
    if w in PUNCH_WORDS:
        return COL_PUNCH
    if w in GO_WORDS:
        return COL_GO
    return COL_HILITE

def wrap_words(draw, words, font):
    # produce lines <= MAX_W with 1–2 lines max
    lines = []
    current = []
    for w in words:
        test = " ".join(current + [w])
        if draw.textlength(test, font=font) <= MAX_W:
            current.append(w)
        else:
            if current:
                lines.append(current)
            current = [w]
    if current:
        lines.append(current)
    return lines

# Build caption "pages": 1–2 lines at a time
# We chunk based on time window (~1.8–2.4s per page)
PAGE_TARGET_SEC = 2.2

pages = []
i = 0
while i < len(word_times):
    page_start = word_times[i][0]
    j = i
    while j < len(word_times) and (word_times[j][1] - page_start) < PAGE_TARGET_SEC:
        j += 1
    # collect words i..j
    words_slice = [wt[2] for wt in word_times[i:j]]
    pages.append((i, j, page_start, word_times[j-1][1] if j > i else page_start + PAGE_TARGET_SEC, words_slice))
    i = j

def render_caption_frame(t):
    # Determine current page and active word
    # Find active word index
    active_idx = None
    for k, (s, e, w) in enumerate(word_times):
        if s <= t < e:
            active_idx = k
            break

    # Find current page containing active word, else nearest previous
    page = None
    for (a, b, ps, pe, ws) in pages:
        if active_idx is not None and a <= active_idx < b:
            page = (a, b, ps, pe, ws)
            break
        if active_idx is None and ps <= t < pe:
            page = (a, b, ps, pe, ws)
            break
    if page is None:
        # fallback last page
        page = pages[-1]

    a, b, ps, pe, ws = page

    # Use hook font for the first ~2.5 seconds
    font = FONT_HOOK if t < 2.6 else FONT_MAIN

    # Make transparent canvas
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Wrap into 1–2 lines
    lines = wrap_words(draw, ws, font)
    if len(lines) > 2:
        lines = [lines[0], lines[1]]  # enforce 2 lines max

    # compute total height
    line_h = font.size + 18
    total_h = len(lines) * line_h
    y0 = TEXT_TOP + (40 if t < 2.6 else 0)

    # render each line word-by-word for highlighting
    for li, line_words in enumerate(lines):
        # center line
        line_text = " ".join(line_words)
        line_w = draw.textlength(line_text, font=font)
        x = int((WIDTH - line_w) // 2)
        y = y0 + li * line_h

        # draw words with individual colors
        cursor = x
        for w in line_words:
            # word index in global slice:
            # approximate by finding first matching forward in [a,b)
            # safer: compute local->global mapping:
            # local index = position in ws, global = a + local
            local_index = ws.index(w)  # ok enough for TTS text; if duplicates same line, still works visually
            global_index = a + local_index

            is_active = (active_idx == global_index)
            col = pick_color(w, is_active)

            # shadow
            draw.text((cursor + 3, y + 3), w, font=font, fill=COL_SHADOW)
            draw.text((cursor, y), w, font=font, fill=col)

            cursor += draw.textlength(w + " ", font=font)

    # subtle dark panel behind captions for readability
    panel_y1 = y0 - 30
    panel_y2 = y0 + total_h + 30
    panel = Image.new("RGBA", (WIDTH, int(panel_y2 - panel_y1)), (0, 0, 0, 90))
    img.alpha_composite(panel, (0, int(panel_y1)))

    return np.array(img)

captions_clip = VideoClip(render_caption_frame, duration=TARGET_SECONDS).set_fps(FPS)

# ---------- 5) BRAND BAR ----------
def make_brand_overlay():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bar_h = 120
    bar = Image.new("RGBA", (WIDTH, bar_h), (10, 90, 200, 235))
    img.paste(bar, (0, HEIGHT - bar_h))

    # auto-fit brand text
    size = 34
    while True:
        f = ImageFont.truetype(FONT_PATH, size)
        bw = draw.textlength(BRAND_TEXT, font=f)
        if bw <= WIDTH - 60 or size <= 22:
            break
        size -= 1

    f = ImageFont.truetype(FONT_PATH, size)
    bw = draw.textlength(BRAND_TEXT, font=f)
    bx = int((WIDTH - bw) // 2)
    by = HEIGHT - bar_h + 38

    draw.text((bx + 2, by + 2), BRAND_TEXT, font=f, fill=(0, 0, 0, 140))
    draw.text((bx, by), BRAND_TEXT, font=f, fill=(255, 255, 255, 255))

    img.save("brand.png")

make_brand_overlay()
brand = ImageClip("brand.png").set_duration(TARGET_SECONDS)

# ---------- 6) COMPOSE + EXPORT ----------
final = CompositeVideoClip([bg, captions_clip, brand], size=(WIDTH, HEIGHT)).set_audio(voice)
final = final.fx(vfx.resize, newsize=(WIDTH, HEIGHT))  # keep exact size

final.write_videofile(
    OUTFILE,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    audio_fps=44100,
    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]
)

print("✅ Video created:", OUTFILE)
