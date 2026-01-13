import textwrap
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, ColorClip, AudioFileClip, ImageClip

# ---------------- SETTINGS ----------------
SCRIPT = (
    "Psychology says your brain avoids uncertainty because it feels unsafe. "
    "That is why routines reduce stress so fast. "
    "When your brain knows what comes next, it conserves energy. "
    "That is why structure improves focus and emotional control. "
    "Follow Brain Fuel Media for daily psychology that actually helps."
)

OUTPUT_VIDEO = "brain_fuel_test.mp4"
WIDTH, HEIGHT = 1080, 1920
FONT_SIZE = 60
BRAND_FONT_SIZE = 36
DURATION = 55  # seconds
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# -----------------------------------------

# 1) Generate voice
tts = gTTS(SCRIPT)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
final_duration = max(DURATION, audio.duration)

# 2) Background (simple dark for now)
background = ColorClip(size=(WIDTH, HEIGHT), color=(15, 15, 15), duration=final_duration)

# 3) Create captions image (PIL)
img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
brand_font = ImageFont.truetype(FONT_PATH, BRAND_FONT_SIZE)

wrapped = textwrap.fill(SCRIPT, width=40)

# Center subtitles
text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
text_w = text_bbox[2] - text_bbox[0]
text_h = text_bbox[3] - text_bbox[1]
text_x = (WIDTH - text_w) // 2
text_y = (HEIGHT - text_h) // 2

draw.multiline_text(
    (text_x, text_y),
    wrapped,
    font=font,
    fill="white",
    align="center"
)

# Branding overlay
brand_text = "YouTube • Brain Fuel Media | IG/TikTok • @Brain.FuelMedia"
brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
brand_w = brand_bbox[2] - brand_bbox[0]
brand_x = (WIDTH - brand_w) // 2
brand_y = HEIGHT - 140

draw.text((brand_x, brand_y), brand_text, font=brand_font, fill="white")

img.save("captions.png")

# 4) Convert captions image to a clip
captions_clip = ImageClip("captions.png").set_duration(final_duration)

# 5) Composite + audio
final = CompositeVideoClip([background, captions_clip]).set_audio(audio)

# 6) Render video
final.write_videofile(
    OUTPUT_VIDEO,
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print("✅ Video generated:", OUTPUT_VIDEO)
