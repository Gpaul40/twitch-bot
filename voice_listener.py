"""
Voice Listener — listens to your mic and triggers bot actions.

Supported voice phrases:
  "clip that" / "clip it" / "save that"  → creates a clip
  "i died" / "death" / "i died again"    → increments death counter
  "shoutout <name>"                       → shoutouts a user in chat
  "start giveaway"                        → starts a giveaway
  "draw giveaway" / "pick winner"         → draws giveaway winner
  "hype" / "let's go" / "let's gooo"     → fires hype message in chat

Run this in a separate terminal while the bot is running:
    python voice_listener.py

Requirements:
    pip install SpeechRecognition pyaudio
    (Windows: if pyaudio fails, run: pip install pipwin && pipwin install pyaudio)
"""

import re
import sys
import time
import httpx
import speech_recognition as sr

DASHBOARD_URL = "http://localhost:8080/api/voice"
COOLDOWN = 3  # seconds between actions to avoid double-triggers

# (regex pattern, command, arg_group)
VOICE_RULES = [
    (r"clip (that|it|this|now)",         "clip",           None),
    (r"save (that|it|the clip)",         "clip",           None),
    (r"(i (just )?died|death|plus one|add death)", "death", None),
    (r"shout\s*out\s+@?(\w+)",           "shoutout",       1),
    (r"start give ?away",                "giveaway_start", None),
    (r"(draw|pick) (give ?away|winner)", "giveaway_draw",  None),
    (r"(hype|let'?s go+|let'?s gooo+)",  "hype",           None),
]


def match_command(text: str):
    t = text.lower().strip()
    for pattern, cmd, arg_group in VOICE_RULES:
        m = re.search(pattern, t)
        if m:
            arg = m.group(arg_group) if arg_group else ""
            return cmd, arg
    return None, None


def send(command: str, arg: str = ""):
    try:
        r = httpx.post(DASHBOARD_URL, json={"command": command, "arg": arg}, timeout=5)
        data = r.json()
        if data.get("ok"):
            print(f"  ✅ {command}: {data.get('result', '')}")
        else:
            print(f"  ⚠️  {command} failed: {data.get('error', '')}")
    except Exception as e:
        print(f"  ❌ Could not reach bot dashboard: {e}")
        print("     Make sure the bot is running (python main.py)")


def main():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.6

    print("🎙️  Voice listener started. Listening for commands...")
    print("    Phrases: 'clip that', 'i died', 'shoutout <name>',")
    print("             'start giveaway', 'draw giveaway', 'hype'\n")

    last_action = 0

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        print("🔊 Mic calibrated. Ready!\n")

        while True:
            try:
                audio = r.listen(source, phrase_time_limit=5)
                text = r.recognize_google(audio)
                print(f"Heard: \"{text}\"")

                cmd, arg = match_command(text)
                if cmd:
                    now = time.time()
                    if now - last_action < COOLDOWN:
                        print("  ⏳ Cooldown — ignored")
                        continue
                    last_action = now
                    send(cmd, arg)

            except sr.UnknownValueError:
                pass  # couldn't understand audio
            except sr.RequestError as e:
                print(f"❌ Speech API error: {e} — check your internet connection")
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n👋 Voice listener stopped.")
                sys.exit(0)


if __name__ == "__main__":
    main()
