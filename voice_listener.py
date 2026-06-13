"""
Voice Listener — listens to your mic and triggers bot actions.

CLIP triggers:
  "clip that/it/this/now", "save that/it", "yo clip that", "bro clip",
  "chat did you see that", "did you see that", "no way bro", "are you kidding",
  "oh my god", "omg", "what was that", "that was insane", "bro what"

DEATH counter:
  "i died", "i just died", "death", "plus one", "add death", "i'm dead",
  "got cooked", "i got bodied", "they cooked me", "i got cooked",
  "that was my fault", "we go again"

HYPE:
  "hype", "let's go", "let's gooo", "let's get it", "we go", "we're cooking",
  "we're on fire", "on fire", "run it back", "we're rolling",
  "different gravy", "built different"

W (post a W in chat):
  "that's a W", "big W", "W in chat", "easy W", "easy work", "too easy",
  "we won", "game", "and game"

RIGGED (funny rigged message):
  "this is rigged", "that's rigged", "rigged", "scripted", "2k scripted",
  "2k rigged", "this game is rigged", "2k hates me"

CLUTCH (hype message for clutch plays):
  "that was clutch", "clutch", "ice in his veins", "cold blooded",
  "in the zone", "locked in", "we're locked in"

GG (gg message in chat):
  "gg", "good game", "ggs"

SHOUTOUT: "shoutout <name>", "big up <name>", "shout <name>"
GIVEAWAY: "start giveaway", "draw giveaway", "pick winner"

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
    # ── CLIP ──────────────────────────────────────────────────────────────
    (r"\b(clip (that|it|this|now)|save (that|it|the clip))\b",         "clip", None),
    (r"\b(yo |bro |chat |aye )?clip (it|that|this)\b",                 "clip", None),
    (r"\b(chat )?(did you see that|bro what|no way bro|are you kidding)\b", "clip", None),
    (r"\b(oh my god|omg|what was that|that was insane|bro that was)\b","clip", None),
    (r"\b(that was (crazy|filthy|dirty|nasty|stupid good|unreal))\b",  "clip", None),
    (r"\bchat (look at this|look at that|you saw that)\b",             "clip", None),

    # ── DEATH ─────────────────────────────────────────────────────────────
    (r"\b(i (just )?died|death|plus one|add death)\b",                 "death", None),
    (r"\b(i'?m dead|i got (bodied|cooked|cooked again|destroyed))\b",  "death", None),
    (r"\b(they cooked me|got cooked|we go again|that was my fault)\b", "death", None),
    (r"\b(bro cooked me|he cooked me|she cooked me)\b",               "death", None),

    # ── HYPE ──────────────────────────────────────────────────────────────
    (r"\b(let'?s go+|let'?s get it|we go|hype)\b",                    "hype", None),
    (r"\b(we'?re (cooking|on fire|rolling)|on fire|run it back)\b",    "hype", None),
    (r"\b(different gravy|built different|no cap fr|we'?re different)\b","hype",None),
    (r"\b(i'?m (cooking|on fire|in the zone)|absolutely cooking)\b",   "hype", None),

    # ── W ─────────────────────────────────────────────────────────────────
    (r"\b(that'?s a w|big w|w in chat|easy w|easy work|too easy)\b",   "w",    None),
    (r"\b(we won|and game|game over|gg easy|we'?re winning)\b",        "w",    None),
    (r"\b(chat w|chat that'?s a w)\b",                                 "w",    None),

    # ── RIGGED ────────────────────────────────────────────────────────────
    (r"\b(this (game )?is rigged|that'?s rigged|rigged|scripted)\b",   "rigged", None),
    (r"\b(2k (scripted|rigged|hates me)|2k is crazy)\b",               "rigged", None),
    (r"\b(how is that (fair|legal)|bro that'?s illegal)\b",            "rigged", None),

    # ── CLUTCH ────────────────────────────────────────────────────────────
    (r"\b(that was clutch|clutch|ice in (my|his|her) veins)\b",        "clutch", None),
    (r"\b(cold blooded|locked in|we'?re locked in|in the zone)\b",     "clutch", None),

    # ── GG ────────────────────────────────────────────────────────────────
    (r"\b(gg'?s?|good game|good games)\b",                             "gg",   None),

    # ── SHOUTOUT ──────────────────────────────────────────────────────────
    (r"\b(shout\s*out|big up|shout)\s+@?(\w+)\b",                      "shoutout", 2),

    # ── GIVEAWAY ──────────────────────────────────────────────────────────
    (r"\bstart give\s*away\b",                                         "giveaway_start", None),
    (r"\b(draw|pick) (give\s*away|winner)\b",                          "giveaway_draw",  None),
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
    print("    CLIP:    'clip that', 'oh my god', 'that was insane', 'did you see that'")
    print("    DEATH:   'i died', 'got cooked', 'i got bodied', 'we go again'")
    print("    HYPE:    'let's go', 'we're cooking', 'different gravy', 'run it back'")
    print("    W:       'that's a W', 'easy work', 'too easy', 'and game'")
    print("    RIGGED:  'this is rigged', '2k scripted', 'that's rigged'")
    print("    CLUTCH:  'clutch', 'ice in my veins', 'locked in'")
    print("    GG:      'gg', 'good game'")
    print("    SHOUT:   'shoutout <name>', 'big up <name>'\n")

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
