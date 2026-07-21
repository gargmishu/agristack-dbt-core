import os

from gtts import gTTS

# Targets matching your exact workflow specifications
OUTPUT_PATH = "./n8n-config/test_audio/ambala-call-771a.wav"
HINDI_PHRASE = "मेरा धान का खेत खराब हो गया है जिला अंबाला में"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

print(f'🎙️ Synthesizing local speech matrix for: "{HINDI_PHRASE}"')

# 🤖 Compile the Hindi vocal articulation array (hi-IN)
tts = gTTS(text=HINDI_PHRASE, lang="hi", slow=False)

# Save the acoustic profile directly to your workspace storage tree
tts.save(OUTPUT_PATH)

print(f"✅ Real spoken audio track generated perfectly at: {OUTPUT_PATH}")
