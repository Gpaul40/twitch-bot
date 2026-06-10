# 🤖 Twitch Bot

A fully-automated Twitch bot with auto-clipping, chat commands, live stream monitoring, Discord alerts, channel point rewards, event handling, chat stats, and a live web dashboard — all in one.

---

## ✨ Features

| Feature | Description |
|---|---|
| ✂️ **Auto-Clipping** | Chat triggers (`clip`, `CLIP`, `POGGERS`…), raids, hype trains — all fire clips automatically |
| 🎬 **Highlight Manager** | After stream ends, ranks clips by views and posts candidates to Discord for one-click highlight promotion |
| 📺 **Stream Monitor** | Polls every 30s — detects go-live/offline, fires Discord alerts, tracks stream duration |
| 🔔 **Discord Alerts** | Go-live, offline, raids, subs, gift subs, new clips, highlight candidates |
| 🎁 **Channel Point Rewards** | Auto-clips on reward redemptions; easily extend with custom rewards |
| 🎉 **Event Handler** | Sub, resub, gift sub, cheer (milestone clips), follow — all handled with chat responses |
| 💬 **Chat Commands** | `!clip`, `!clips`, `!topclips`, `!mystats`, `!topchatters`, `!so`, `!lurk`, `!game`, `!title`, `!uptime` |
| 📊 **Stats Tracking** | Per-user message counts and event log in local SQLite DB |
| 🖥️ **Web Dashboard** | Live dashboard at `http://localhost:8080` — stream status, top chatters, recent clips, session clips |
| 🔑 **Token Auto-Refresh** | OAuth tokens auto-refresh using your refresh token — no manual re-auth |

---

## 🚀 Setup

### 1. Get Twitch Credentials

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console) → **Register Your Application**  
   Redirect URL: `http://localhost`
2. Copy your **Client ID** and **Client Secret**
3. Generate an OAuth token with these scopes using [Twitch Token Generator](https://twitchtokengenerator.com/):
   - `clips:edit`
   - `channel:read:redemptions`
   - `channel:read:hype_train`
   - `chat:read` + `chat:edit`
   - `user:read:follows`
4. Find your **Broadcaster ID** (numeric): [streamweasels.com lookup](https://www.streamweasels.com/tools/convert-twitch-username-to-user-id/)
5. (Optional) Create a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668) for alerts

### 2. Configure `.env`

```bash
cp .env.example .env
# Fill in all values
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

Then open **http://localhost:8080** for the live dashboard.

---

## 📁 Project Structure

```
twitch-bot/
├── main.py                       # Entry point — runs bot + dashboard together
├── requirements.txt
├── .env.example
├── bot/
│   ├── config.py                 # Config loader with startup validation
│   ├── core.py                   # Bot class — wires everything together
│   ├── helix.py                  # Twitch Helix API client + token auto-refresh
│   ├── stream_monitor.py         # Background stream poller (go-live/offline/hype train)
│   ├── clipping/
│   │   ├── clipper.py            # Auto-clip engine
│   │   └── highlight.py          # Post-stream highlight candidate tracker
│   ├── stats/
│   │   └── tracker.py            # SQLite chat & event stats
│   ├── alerts/
│   │   └── discord.py            # Discord webhook alerts
│   ├── rewards/
│   │   └── handler.py            # Channel point reward handler
│   ├── events/
│   │   └── handler.py            # Sub, resub, giftsub, cheer, follow events
│   └── commands/
│       ├── general.py            # !so, !lurk, !game, !title, !uptime
│       ├── clips.py              # !clip, !clips, !topclips
│       └── stats.py              # !mystats, !topchatters
├── dashboard/
│   ├── app.py                    # FastAPI dashboard app
│   └── templates/index.html      # Live dashboard UI
├── data/                         # SQLite DB (gitignored)
└── logs/                         # Log files (gitignored)
```

---

## 💬 Chat Commands

| Command | Description |
|---|---|
| `!clip` | Manually create a clip |
| `!clips` | Show 3 most recent clips |
| `!topclips` | Show top 5 clips by views |
| `!mystats` | Your message count |
| `!topchatters` | Top 10 chatters |
| `!so <user>` | Shoutout a user |
| `!lurk` | Lurk message |
| `!game` | Current game being played |
| `!title` | Current stream title |
| `!uptime` | How long stream has been live |

---

## 🎬 Highlights

After your stream ends, the bot automatically:
1. Looks up all clips created this session
2. Ranks them by view count
3. Posts the top 5 to Discord as highlight candidates
4. You promote them to highlights in one click at [dashboard.twitch.tv/videos](https://dashboard.twitch.tv/videos)

---

## 🔧 Adding Custom Channel Point Rewards

Edit `bot/rewards/handler.py`:

```python
elif "hydrate" in reward_title:
    channel = self.bot.get_channel(self.bot.cfg.channel)
    await channel.send(f"💧 {username} says: drink water!")
```

