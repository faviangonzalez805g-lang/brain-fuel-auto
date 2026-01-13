from gtts import gTTS
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import textwrap

# -------- SETTINGS --------
SCRIPT = (
    "Psychology says your brain avoids uncertainty because it feels unsafe. "
    "That is why routines reduce stress so fast. "
    "When your brain knows what comes next, it conserves energy. "
    "That is why structure improves focus and emotional control."
)

OUTPUT_VIDEO = "brain_fuel_test.mp4"
WIDTH, HEIGHT = 1080, 1920
DURATION = 55  # seconds
# --------------------------

# Generate voice
tts = gTTS(SCRIPT)
tts.save("voice.mp3")

# Background
background = ColorClip(size=(WIDTH, HEIGHT), color=(15, 15, 15), duration=DURATION)

# Wrap subtitles
wrapped_text = "\n".join(textwrap.wrap(SCRIPT, 40))

subtitles = TextClip(
    wrapped_text,
    fontsize=60,
    color="white",
    size=(900, None),
    method="caption",
).set_position(("center", "center")).set_duration(DURATION)

# Branding overlay
branding = TextClip(
    "YouTube • Brain Fuel Media | IG/TikTok • @Brain.FuelMedia",
    fontsize=35,
    color="white"
).set_position(("center", HEIGHT - 120)).set_duration(DURATION)

# Combine
video = CompositeVideoClip([background, subtitles, branding])
video = video.set_audio("voice.mp3")

video.write_videofile(
    OUTPUT_VIDEO,
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

print("Video generated:", OUTPUT_VIDEO)
