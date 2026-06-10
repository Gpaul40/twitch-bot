# 🤖 Twitch Bot

An automated Twitch bot with auto-clipping, chat commands, stream alerts, channel point rewards, and chat stats.

---

## ✨ Features

| Feature | Description |
|---|---|
| ✂️ **Auto-Clipping** | Clips automatically when chat types a trigger word (`clip`, `CLIP`, etc.), on raids, or hype trains |
| 💬 **Chat Commands** | `!clip`, `!clips`, `!mystats`, `!topchatters`, `!so`, `!lurk`, `!commands` |
| 🔔 **Discord Alerts** | Posts to a Discord webhook on go-live, raids, subs, and new clips |
| 🎁 **Channel Point Rewards** | Auto-clips on "clip" reward redemptions; easily extend with custom rewards |
| 📊 **Stats Tracking** | Tracks messages per user in a local SQLite DB |

---

## 🚀 Setup

### 1. Get Twitch Credentials

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console) → **Register Your Application**
2. Copy your **Client ID** and **Client Secret**
3. Generate an OAuth token with the required scopes:
   - `clips:edit` — to create clips
   - `channel:read:redemptions` — for channel point rewards
   - `chat:read` + `chat:edit` — for chat bot

   Use the [Twitch Token Generator](https://twitchtokengenerator.com/) or Twitch CLI.

4. Find your **Broadcaster ID** (numeric) — use [this lookup tool](https://www.streamweasels.com/tools/convert-twitch-username-to-user-id/).

### 2. Configure `.env`

```bash
cp .env.example .env
# Fill in your values
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

---

## 📁 Project Structure

```
twitch-bot/
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
├── bot/
│   ├── core.py              # Bot class — wires everything together
│   ├── clipping/
│   │   └── clipper.py       # Auto-clip engine (Helix API)
│   ├── stats/
│   │   └── tracker.py       # SQLite chat stats
│   ├── alerts/
│   │   └── discord.py       # Discord webhook alerts
│   ├── rewards/
│   │   └── handler.py       # Channel point reward handler
│   └── commands/
│       ├── general.py       # !so, !lurk, !uptime, !commands
│       ├── clips.py         # !clip, !clips
│       └── stats.py         # !mystats, !topchatters
├── data/                    # SQLite DB (gitignored)
└── logs/                    # Log files (gitignored)
```

---

## 🔧 Adding Custom Channel Point Rewards

Edit `bot/rewards/handler.py`:

```python
elif "hydrate" in reward_title:
    await event.channel.send(f"@{username} 💧 Drink water!")
```

---

## 📋 Chat Commands

| Command | Description |
|---|---|
| `!clip` | Manually create a clip |
| `!clips` | Show 3 most recent clips |
| `!mystats` | Your message count |
| `!topchatters` | Top 5 chatters |
| `!so <user>` | Shoutout a user |
| `!lurk` | Lurk message |
| `!commands` | List all commands |
