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
FONT_MAIN = ImageFont.truetype(FONT_PATH, 70)
FONT_HOOK = ImageFont.truetype(FONT_PATH, 78)

COL_NORMAL = (255, 255, 255, 235)
COL_HILITE = (255, 220, 0, 255)
COL_PUNCH  = (255, 70, 70, 255)
COL_GO     = (80, 255, 120, 255)
COL_SHADOW = (0, 0, 0, 190)

PUNCH_WORDS = set(["danger", "stressed", "stress", "anxiety", "trick", "dont", "don't", "restart"])
GO_WORDS = set(["follow", "start", "return", "build", "tiny", "two", "minutes"])

SAFE_X = 80
TEXT_TOP = int(HEIGHT * 0.30)
MAX_W = WIDTH - SAFE_X * 2

def pick_color(word, is_active):
    w = word.lower().replace("’", "'")
    if not is_active:
        return COL_NORMAL
    if w in PUNCH_WORDS:
        return COL_PUNCH
    if w in GO_WORDS:
        return COL_GO
    return COL_HILITE

def wrap_words(draw, words, font):
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

PAGE_TARGET_SEC = 2.2
pages = []
i = 0
while i < len(word_times):
    page_start = word_times[i][0]
    j = i
    while j < len(word_times) and (word_times[j][1] - page_start) < PAGE_TARGET_SEC:
        j += 1
    if j == i:
        j += 1
    words_slice = [wt[2] for wt in word_times[i:j]]
    pages.append((i, j, page_start, word_times[j-1][1], words_slice))
    i = j

def caption_rgba_frame(t):
    active_idx = None
    for k, (s, e, _) in enumerate(word_times):
        if s <= t < e:
            active_idx = k
            break

    page = None
    for (a, b, ps, pe, ws) in pages:
        if active_idx is not None and a <= active_idx < b:
            page = (a, b, ps, pe, ws)
            break
        if active_idx is None and ps <= t < pe:
            page = (a, b, ps, pe, ws)
            break
    if page is None:
        page = pages[-1]

    a, b, ps, pe, ws = page
    font = FONT_HOOK if t < 2.6 else FONT_MAIN

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # semi-dark panel for readability
    panel_h = 340
    panel_y = TEXT_TOP - 40
    panel = Image.new("RGBA", (WIDTH, panel_h), (0, 0, 0, 120))
    img = paste_rgba_safe(img, panel, (0, panel_y))

    lines = wrap_words(draw, ws, font)
    if len(lines) > 2:
        lines = [lines[0], lines[1]]

    line_h = font.size + 18
    y0 = TEXT_TOP + (30 if t < 2.6 else 0)

    local_map = ws[:]
    for li, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        line_w = draw.textlength(line_text, font=font)
        x = int((WIDTH - line_w) // 2)
        y = y0 + li * line_h

        cursor = x
        for idx_local, w in enumerate(line_words):
            try:
                local_pos = local_map.index(w)
            except ValueError:
                local_pos = idx_local

            global_index = a + local_pos
            is_active = (active_idx == global_index)
            col = pick_color(w, is_active)

            draw.text((cursor + 3, y + 3), w, font=font, fill=COL_SHADOW)
            draw.text((cursor, y), w, font=font, fill=col)

            cursor += draw.textlength(w + " ", font=font)
            if local_pos < len(local_map):
                local_map[local_pos] = "\0"

    return np.array(img)

def caption_rgb(t):
    rgba = caption_rgba_frame(t)
    return rgba[:, :, :3]

def caption_mask(t):
    rgba = caption_rgba_frame(t)
    return (rgba[:, :, 3] / 255.0).astype(np.float32)

captions_rgb = VideoClip(caption_rgb, duration=TARGET_SECONDS).set_fps(FPS)
captions_m = VideoClip(caption_mask, duration=TARGET_SECONDS, ismask=True).set_fps(FPS)
captions_clip = captions_rgb.set_mask(captions_m)

# ---------- 5) BRAND BAR ----------
def make_brand_overlay():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bar_h = 120
    bar = Image.new("RGBA", (WIDTH, bar_h), (0, 0, 0, 180))
    img = paste_rgba_safe(img, bar, (0, HEIGHT - bar_h))

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

    draw.text((bx + 2, by + 2), BRAND_TEXT, font=f, fill=(0, 0, 0, 160))
    draw.text((bx, by), BRAND_TEXT, font=f, fill=(255, 255, 255, 255))
    img.save("brand.png")

make_brand_overlay()
brand = ImageClip("brand.png").set_duration(TARGET_SECONDS)

# ---------- 6) COMPOSE + EXPORT ----------
final = CompositeVideoClip([bg, captions_clip, brand], size=(WIDTH, HEIGHT)).set_audio(voice)

final.write_videofile(
    OUTFILE,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    audio_fps=44100,
    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]
)

print("✅ Video created:", OUTFILE)
