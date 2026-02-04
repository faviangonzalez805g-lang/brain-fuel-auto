import os, math, random, re
import numpy as np
import requests
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, AudioFileClip, ImageClip, VideoClip

# ===================== SETTINGS =====================
WIDTH, HEIGHT = 1080, 1920
FPS = 30
TARGET_SECONDS = 62
VOICE_SPEED = 1.18

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BRAND_TEXT = "YouTube: Brain Fuel Media   |   IG/TikTok: @Brain.FuelMedia"
OUTFILE = "brain_fuel_final.mp4"

# Pick 1 niche to start (don’t change daily)
SUBREDDIT = "AmItheAsshole"   # try: MaliciousCompliance, TrueOffMyChest
# ===================================================

def sh(cmd: str):
    os.system(cmd + " >/dev/null 2>&1")

def ensure_file(path: str):
    return os.path.exists(path) and os.path.getsize(path) > 10000

def fetch_reddit_post(subreddit: str):
    """
    Uses Reddit's public JSON endpoint (no auth). We grab top hot post.
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
    headers = {"User-Agent": "brainfuel-bot/0.1 (by u/brainfuel)"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    posts = []
    for child in data["data"]["children"]:
        d = child["data"]
        # filter out stickies / very short / links
        if d.get("stickied"):
            continue
        title = (d.get("title") or "").strip()
        selftext = (d.get("selftext") or "").strip()
        if len(title) < 20:
            continue
        if len(selftext) < 200:
            continue
        posts.append((title, selftext))
    if not posts:
        # fallback: use title only
        for child in data["data"]["children"]:
            d = child["data"]
            title = (d.get("title") or "").strip()
            if len(title) > 20:
                return title, ""
        raise RuntimeError("No usable posts found")
    return random.choice(posts)

def shorten(text, max_chars):
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].rsplit(" ", 1)[0] + "..."

def build_script(title, body):
    """
    IMPORTANT: We paraphrase/summarize (not verbatim) to avoid copy issues.
    We also aim for ~60s pacing.
    """
    title_clean = re.sub(r"\s+", " ", title).strip()

    # Take a small chunk and summarize into bullet-like sentences (simple rules)
    body_clean = re.sub(r"\s+", " ", body).strip()
    body_chunk = shorten(body_clean, 900) if body_clean else ""

    hook = f"Quick story from Reddit: {shorten(title_clean, 110)}"
    setup = "Here’s the short version."
    # crude “summary”: break into 3-5 sentence chunks by punctuation
    parts = re.split(r"(?<=[.!?])\s+", body_chunk)
    parts = [p.strip() for p in parts if len(p.strip()) > 40]

    # pick 4 parts max and paraphrase lightly (remove quotes, extra details)
    selected = parts[:4] if parts else []
    summary_lines = []
    for p in selected:
        p = re.sub(r"\".*?\"", "", p)
        p = re.sub(r"\(.*?\)", "", p)
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) > 180:
            p = shorten(p, 180)
        summary_lines.append(p)

    lesson = "Psych tip: when emotions spike, slow down and ask what outcome you actually want."
    cta = "Follow Brain Fuel Media for daily mind shifts."

    script = " ".join([hook, setup] + summary_lines + [lesson, cta])

    # Add pacing fillers if too short
    fillers = [
        "Now here’s the wild part.",
        "And this is where it gets messy.",
        "Here’s what most people miss.",
        "Think about it like this."
    ]
    while len(script.split()) < 155:  # ~60s at this voice speed
        script += " " + random.choice(fillers)

    return script

def clean_words(text):
    text = re.sub(r"[^a-zA-Z0-9'’\s]", "", text)
    return [w for w in text.split() if w.strip()]

# ---------- AUDIO ----------
title, body = fetch_reddit_post(SUBREDDIT)
SCRIPT = build_script(title, body)

gTTS(SCRIPT, slow=False).save("voice_raw.mp3")
sh(
    f'ffmpeg -y -i voice_raw.mp3 '
    f'-filter:a "atempo={VOICE_SPEED},loudnorm=I=-16:TP=-1.5:LRA=11" '
    f'voice_fast.mp3'
)

# loop to exact duration
sh(f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} -c copy voice_loop.mp3')
if not ensure_file("voice_loop.mp3"):
    sh(
        f'ffmpeg -y -stream_loop -1 -i voice_fast.mp3 -t {TARGET_SECONDS} '
        f'-c:a libmp3lame -q:a 4 voice_loop.mp3'
    )

voice = AudioFileClip("voice_loop.mp3").set_duration(TARGET_SECONDS)

# ---------- WORD TIMING (uniform, looks good with TTS) ----------
WORDS = clean_words(SCRIPT)
audio_dur = max(1.0, min(voice.duration, TARGET_SECONDS))
wps = max(2.0, len(WORDS) / audio_dur)

word_times = []
t = 0.0
for w in WORDS:
    base = 1.0 / wps
    bonus = min(0.08, max(0.0, (len(w) - 6) * 0.01))
    dt = base + bonus
    word_times.append((t, min(t + dt, TARGET_SECONDS), w))
    t += dt
word_times = [(s, e, w) for (s, e, w) in word_times if s < TARGET_SECONDS]

# ---------- BACKGROUND VISUALS (RGB ONLY) ----------
random.seed(7)
particles = []
for _ in range(70):
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

    base = 10 + 25 * (1 - Y)
    wave1 = 70 * (np.sin(2 * math.pi * (X * 1.1 + t * 0.05)) * 0.5 + 0.5)
    wave2 = 60 * (np.sin(2 * math.pi * (Y * 1.4 - t * 0.06)) * 0.5 + 0.5)

    r = base + 0.22 * wave2
    g = base + 0.45 * wave1
    b = base + 1.05 * wave1 + 0.55 * wave2

    frame = np.clip(np.dstack([r, g, b]), 0, 255).astype(np.uint8)
    img = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    for p in particles:
        px = int((p["x"] + math.sin(t * p["spd"] + p["phase"]) * 0.02) * w)
        py = int((p["y"] + math.cos(t * p["spd"] + p["phase"]) * 0.03) * h)
        rr = p["r"]
        draw.ellipse((px-rr*3, py-rr*3, px+rr*3, py+rr*3), fill=(255, 255, 255, 18))
        draw.ellipse((px-rr, py-rr, px+rr, py+rr), fill=(255, 255, 255, 55))

    return np.array(img)  # RGB

bg = VideoClip(make_bg_frame, duration=TARGET_SECONDS).set_fps(FPS)

# ---------- CAPTIONS: 1–2 lines + word highlight ----------
FONT_MAIN = ImageFont.truetype(FONT_PATH, 70)
FONT_HOOK = ImageFont.truetype(FONT_PATH, 78)

COL_NORMAL = (255, 255, 255, 235)
COL_HILITE = (255, 220, 0, 255)
COL_PUNCH  = (255, 70, 70, 255)
COL_GO     = (80, 255, 120, 255)
COL_SHADOW = (0, 0, 0, 190)

PUNCH_WORDS = set(["danger", "stressed", "stress", "anxiety", "wild", "messy"])
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
    ws = [wt[2] for wt in word_times[i:j]]
    pages.append((i, j, page_start, word_times[j-1][1], ws))
    i = j

def render_caption_frame(t):
    active_idx = None
    for k, (s, e, _) in enumerate(word_times):
        if s <= t < e:
            active_idx = k
            break

    page = None
    for (a, b, ps, pe, ws) in pages:
        if active_idx is not None and a <= active_idx < b:
            page = (a, b, ws)
            break
        if active_idx is None and ps <= t < pe:
            page = (a, b, ws)
            break
    if page is None:
        page = (pages[-1][0], pages[-1][1], pages[-1][4])

    a, b, ws = page
    font = FONT_HOOK if t < 2.6 else FONT_MAIN

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # panel behind text
    panel = Image.new("RGBA", (WIDTH, 340), (0, 0, 0, 120))
    img.alpha_composite(panel, (0, TEXT_TOP - 40))

    lines = wrap_words(draw, ws, font)
    if len(lines) > 2:
        lines = [lines[0], lines[1]]

    line_h = font.size + 18
    y0 = TEXT_TOP + (30 if t < 2.6 else 0)

    # local map for duplicate-safe matching
    local_map = ws[:]

    for li, line_words in enumerate(lines):
        line_text = " ".join(line_words)
        line_w = draw.textlength(line_text, font=font)
        x = int((WIDTH - line_w) // 2)
        y = y0 + li * line_h

        cursor = x
        for w in line_words:
            try:
                local_pos = local_map.index(w)
            except ValueError:
                local_pos = 0
            global_index = a + local_pos
            is_active = (active_idx == global_index)
            col = pick_color(w, is_active)

            draw.text((cursor + 3, y + 3), w, font=font, fill=COL_SHADOW)
            draw.text((cursor, y), w, font=font, fill=col)

            cursor += draw.textlength(w + " ", font=font)

            # consume for duplicates
            if local_pos < len(local_map):
                local_map[local_pos] = "\0"

    return np.array(img.convert("RGBA"))

def render_caption_rgba(t):
    frame = render_caption_frame(t)
    if frame.shape[2] == 3:
        alpha = np.full((frame.shape[0], frame.shape[1], 1), 255, dtype=np.uint8)
        frame = np.concatenate([frame, alpha], axis=2)
    return frame

captions_rgba = VideoClip(render_caption_rgba, duration=TARGET_SECONDS).set_fps(FPS)
captions_mask = VideoClip(
    lambda t: (render_caption_rgba(t)[:, :, 3].astype(np.float32) / 255.0),
    duration=TARGET_SECONDS
).set_fps(FPS)
captions = captions_rgba.set_mask(captions_mask)

# ---------- BRAND BAR ----------
def make_brand_overlay():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bar_h = 120
    bar = Image.new("RGBA", (WIDTH, bar_h), (10, 90, 200, 235))
    img.paste(bar, (0, HEIGHT - bar_h))

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

# ---------- COMPOSE ----------
final = CompositeVideoClip([bg, captions, brand], size=(WIDTH, HEIGHT)).set_audio(voice)

final.write_videofile(
    OUTFILE,
    fps=FPS,
    codec="libx264",
    audio_codec="aac",
    audio_fps=44100,
    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"]
)

print("✅ Done:", OUTFILE)
print("Source subreddit:", SUBREDDIT)
print("Post title:", title)
