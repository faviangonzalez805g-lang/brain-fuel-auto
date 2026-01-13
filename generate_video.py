import textwrap
from gtts import gTTS
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, AudioFileClip

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
DURATION = 55  # seconds (keep 50-58 for Shorts)
FONT = "DejaVu-Sans"
# -----------------------------------------

# 1) Generate voice (TTS)
tts = gTTS(SCRIPT)
tts.save("voice.mp3")

audio = AudioFileClip("voice.mp3")

# If voice is shorter than DURATION, we keep background running; if longer, extend duration.
final_duration = max(DURATION, audio.duration)

# 2) Background (simple dark background for now)
background = ColorClip(size=(WIDTH, HEIGHT), color=(15, 15, 15), duration=final_duration)

# 3) Subtitles (wrap script)
wrapped_text = "\n".join(textwrap.wrap(SCRIPT, 40))

subtitles = TextClip(
    wrapped_text,
    fontsize=60,
    color="white",
    font=FONT,
    size=(900, None),
    method="caption",
).set_position(("center", "center")).set_duration(final_duration)

# 4) Branding overlay (your socials)
branding = TextClip(
    "YouTube • Brain Fuel Media | IG/TikTok • @Brain.FuelMedia",
    fontsize=35,
    color="white",
    font=FONT,
).set_position(("center", HEIGHT - 120)).set_duration(final_duration)

# 5) Combine layers
video = CompositeVideoClip([background, subtitles, branding]).set_audio(audio)

# 6) Render MP4
video.write_videofile(
    OUTPUT_VIDEO,
    fps=30,
    codec="libx264",
    audio_codec="aac",
)

print("Video generated:", OUTPUT_VIDEO)
