"""
FastAPI dashboard — live stats, recent clips, stream status.
Runs alongside the bot on port 8080 (configurable).
"""

import os
import time
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiosqlite

# Injected at runtime by main.py
_bot = None

# In-memory session state
_wl = {"wins": 0, "losses": 0}
_last_clip = {"count": 0, "triggered_by": "", "url": "", "ts": 0.0}
_follow_goal = {"goal": 500, "current": 0}
_sub_goal = {"goal": 10, "current": 0}
_sub_count_session = 0


def set_bot(bot):
    global _bot
    _bot = bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Twitch Bot Dashboard", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")


# ------------------------------------------------------------------ #
#  Pages                                                               #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/overlay/deaths", response_class=HTMLResponse)
async def overlay_deaths(request: Request):
    return templates.TemplateResponse("overlay_deaths.html", {"request": request})


@app.get("/overlay/wl", response_class=HTMLResponse)
async def overlay_wl(request: Request):
    return templates.TemplateResponse("overlay_wl.html", {"request": request})


@app.get("/overlay/alert", response_class=HTMLResponse)
async def overlay_alert(request: Request):
    return templates.TemplateResponse("overlay_alert.html", {"request": request})


@app.get("/overlay/follow_goal", response_class=HTMLResponse)
async def overlay_follow_goal(request: Request):
    return templates.TemplateResponse("overlay_follow_goal.html", {"request": request})


@app.get("/overlay/sub_goal", response_class=HTMLResponse)
async def overlay_sub_goal(request: Request):
    return templates.TemplateResponse("overlay_sub_goal.html", {"request": request})


@app.get("/overlay/nowplaying", response_class=HTMLResponse)
async def overlay_nowplaying(request: Request):
    return templates.TemplateResponse("overlay_nowplaying.html", {"request": request})


# ------------------------------------------------------------------ #
#  API endpoints                                                       #
# ------------------------------------------------------------------ #

@app.get("/api/status")
async def api_status():
    if not _bot:
        return {"live": False, "stream": None}
    monitor = _bot.stream_monitor
    stream = monitor.current_stream
    uptime = ""
    if monitor._stream_start:
        delta = datetime.now(timezone.utc) - monitor._stream_start
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        uptime = f"{h}h {m}m"
    return {
        "live": monitor.is_live,
        "uptime": uptime,
        "stream": {
            "title": stream.get("title", "") if stream else "",
            "game": stream.get("game_name", "") if stream else "",
            "viewers": stream.get("viewer_count", 0) if stream else 0,
            "thumbnail": (stream.get("thumbnail_url", "")
                          .replace("{width}", "440").replace("{height}", "248")) if stream else "",
        } if stream else None,
        "channel": _bot.cfg.channel,
    }


@app.get("/api/clips")
async def api_clips():
    if not _bot:
        return []
    clips = await _bot.helix.get_clips(_bot.cfg.broadcaster_id, first=10)
    return [{"title": c.get("title"), "url": c.get("url"), "views": c.get("view_count", 0),
             "thumbnail": c.get("thumbnail_url", "")} for c in clips]


@app.get("/api/stats")
async def api_stats():
    if not _bot:
        return {}
    db_path = _bot.cfg.stats_db
    try:
        async with aiosqlite.connect(db_path) as db:
            msg_row = await (await db.execute("SELECT COUNT(*) FROM messages")).fetchone()
            top_row = await (await db.execute(
                "SELECT username, COUNT(*) c FROM messages GROUP BY username ORDER BY c DESC LIMIT 10"
            )).fetchall()
            event_rows = await (await db.execute(
                "SELECT event_type, COUNT(*) c FROM events GROUP BY event_type ORDER BY c DESC"
            )).fetchall()
        return {
            "total_messages": msg_row[0] if msg_row else 0,
            "top_chatters": [{"user": r[0], "count": r[1]} for r in top_row],
            "events": [{"type": r[0], "count": r[1]} for r in event_rows],
        }
    except Exception:
        return {}


@app.get("/api/session_clips")
async def api_session_clips():
    if not _bot:
        return []
    return _bot.highlight_mgr._session_clips


@app.get("/api/queue")
async def api_queue():
    if not _bot:
        return []
    cog = _bot.queue_cog
    return cog.queue if cog else []


@app.get("/api/giveaway")
async def api_giveaway():
    if not _bot:
        return {"active": False, "entries": 0}
    cog = _bot.fun_cog
    if not cog:
        return {"active": False, "entries": 0}
    return {"active": cog.giveaway_active, "entries": cog.giveaway_entry_count}


@app.get("/api/deaths")
async def api_deaths():
    if not _bot:
        return {"count": 0}
    count = await _bot.stats.get_deaths()
    return {"count": count}


@app.get("/api/wl")
async def api_wl():
    return _wl


@app.get("/api/last_clip")
async def api_last_clip():
    return _last_clip


@app.get("/api/follow_goal")
async def api_follow_goal():
    # Try to get real follower count from Helix
    if _bot:
        try:
            data = await _bot.helix._get("/channels/followers",
                                         params={"broadcaster_id": _bot.cfg.broadcaster_id, "first": "1"})
            if data:
                _follow_goal["current"] = data.get("total", _follow_goal["current"])
        except Exception:
            pass
    return _follow_goal


@app.get("/api/sub_goal")
async def api_sub_goal():
    global _sub_count_session
    return {"current": _sub_count_session, "goal": _sub_goal["goal"]}


@app.get("/api/points")
async def api_points(user: str = ""):
    if not _bot or not hasattr(_bot, 'loyalty') or not user:
        return {"balance": 0}
    bal = await _bot.loyalty.get_points(user)
    return {"username": user, "balance": bal}


@app.get("/api/top_points")
async def api_top_points():
    if not _bot or not hasattr(_bot, 'loyalty'):
        return []
    top = await _bot.loyalty.get_top(10)
    return [{"username": r[0], "balance": r[1]} for r in top]


@app.post("/api/set_goal")
async def api_set_goal(request: Request):
    """Set follow or sub goal: {"type": "follow"/"sub", "goal": 500}"""
    global _follow_goal, _sub_goal
    data = await request.json()
    gtype = data.get("type", "").lower()
    goal = int(data.get("goal", 0))
    if gtype == "follow":
        _follow_goal["goal"] = goal
        return {"ok": True}
    elif gtype == "sub":
        _sub_goal["goal"] = goal
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "type must be follow or sub"}, status_code=400)


@app.get("/api/stream_recap")
async def api_stream_recap():
    """Full stream recap — for end-of-stream Discord embed."""
    if not _bot:
        return {}
    monitor = _bot.stream_monitor
    duration = ""
    if monitor._stream_start:
        delta = datetime.now(timezone.utc) - monitor._stream_start
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        duration = f"{h}h {m}m"
    try:
        top = await _bot.stats.get_top_chatters(5)
        top_chatters = [r[0] for r in top]
    except Exception:
        top_chatters = []
    stream = monitor.current_stream or {}
    return {
        "title": stream.get("title", ""),
        "game": stream.get("game_name", ""),
        "duration": duration,
        "peak_viewers": stream.get("viewer_count", 0),
        "clips_this_session": len(_bot.highlight_mgr._session_clips),
        "deaths": await _bot.stats.get_deaths(),
        "wl": dict(_wl),
        "top_chatters": top_chatters,
        "sub_count": _sub_count_session,
    }


# ------------------------------------------------------------------ #
#  Voice / action endpoints                                            #
# ------------------------------------------------------------------ #

@app.post("/api/voice_action")
async def api_voice_action(request: Request):
    """Simple non-chat actions: reset_deaths, reset_wl, win, loss."""
    data = await request.json()
    action = data.get("action", "").strip().lower()

    if action == "reset_deaths":
        if _bot:
            await _bot.stats.reset_deaths()
        return {"ok": True}

    elif action == "reset_wl":
        _wl["wins"] = 0
        _wl["losses"] = 0
        return {"ok": True}

    elif action == "win":
        _wl["wins"] += 1
        if _bot:
            ch = _bot.get_channel(_bot.cfg.channel)
            if ch:
                await ch.send(f"✅ W secured! Record: {_wl['wins']}W – {_wl['losses']}L 🏆")
        return {"ok": True, "result": f"{_wl['wins']}W {_wl['losses']}L"}

    elif action == "loss":
        _wl["losses"] += 1
        if _bot:
            ch = _bot.get_channel(_bot.cfg.channel)
            if ch:
                await ch.send(f"❌ L registered. Record: {_wl['wins']}W – {_wl['losses']}L. Run it back!")
        return {"ok": True, "result": f"{_wl['wins']}W {_wl['losses']}L"}

    return JSONResponse({"ok": False, "error": f"Unknown action: {action}"}, status_code=400)


@app.post("/api/voice")
async def api_voice(request: Request):
    """
    Accepts: {"command": "clip"} etc.
    """
    global _last_clip
    if not _bot:
        return JSONResponse({"ok": False, "error": "Bot not ready"}, status_code=503)

    data = await request.json()
    cmd = data.get("command", "").strip().lower()
    arg = data.get("arg", "").strip()

    channel = _bot.get_channel(_bot.cfg.channel)
    if not channel:
        return JSONResponse({"ok": False, "error": "Channel not connected"}, status_code=503)

    if cmd == "clip":
        if not _bot.stream_monitor.is_live:
            return {"ok": False, "error": "Stream is offline"}
        if _bot.clipper._on_cooldown():
            return {"ok": False, "error": "Clip on cooldown"}
        clip = await _bot.clipper.create_clip(
            _bot.cfg.broadcaster_id, title="Voice clip", triggered_by="voice"
        )
        if clip:
            from bot.clipping.clipper import Clipper
            url = Clipper.public_url(clip)
            _bot.highlight_mgr.record_clip(clip)
            _last_clip = {"count": _last_clip["count"] + 1, "triggered_by": "voice", "url": url, "ts": time.time()}
            await channel.send(f"✂️ Voice clip saved! {url}")
            return {"ok": True, "result": url}
        return {"ok": False, "error": "Clip creation failed"}

    elif cmd == "death":
        count = await _bot.stats.increment_deaths()
        await channel.send(f"💀 {_bot.cfg.channel} has died {count} time(s) this stream! F in chat")
        return {"ok": True, "result": str(count)}

    elif cmd == "shoutout":
        if not arg:
            return {"ok": False, "error": "No user specified"}
        await channel.send(f"🎙️ Go check out @{arg} at https://twitch.tv/{arg} — show them some love! ❤️")
        return {"ok": True, "result": f"Shouted out {arg}"}

    elif cmd == "giveaway_start":
        cog = _bot.fun_cog
        if cog:
            cog._giveaway_active = True
            cog._giveaway_entries.clear()
            await channel.send("🎉 Giveaway started! Type !enter to participate!")
        return {"ok": True, "result": "Giveaway started"}

    elif cmd == "giveaway_draw":
        cog = _bot.fun_cog
        if cog and cog._giveaway_entries:
            winner = random.choice(list(cog._giveaway_entries))
            cog._giveaway_entries.discard(winner)
            await channel.send(f"🏆 Congratulations @{winner}! You won the giveaway! 🎉")
            return {"ok": True, "result": winner}
        return {"ok": False, "error": "No entries"}

    elif cmd == "hype":
        await channel.send("🔥🔥🔥 LETS GOOO! PogChamp PogChamp PogChamp 🔥🔥🔥")
        return {"ok": True, "result": "Hype sent"}

    elif cmd == "w":
        _wl["wins"] += 1
        await channel.send(f"🏆 W IN CHAT!! Record: {_wl['wins']}W – {_wl['losses']}L 🔥")
        return {"ok": True, "result": f"{_wl['wins']}W {_wl['losses']}L"}

    elif cmd == "loss":
        _wl["losses"] += 1
        await channel.send(f"❌ L registered. Record: {_wl['wins']}W – {_wl['losses']}L. Run it back!")
        return {"ok": True, "result": f"{_wl['wins']}W {_wl['losses']}L"}

    elif cmd == "win":
        _wl["wins"] += 1
        await channel.send(f"✅ W secured! Record: {_wl['wins']}W – {_wl['losses']}L 🏆")
        return {"ok": True, "result": f"{_wl['wins']}W {_wl['losses']}L"}

    elif cmd == "rigged":
        await channel.send("💀 RIGGED!! 2K does NOT want us to win chat 😭 the scripting is REAL")
        return {"ok": True, "result": "Rigged sent"}

    elif cmd == "clutch":
        await channel.send("🧊 ICE IN THE VEINS!! What a play! clutchPog 🔥")
        return {"ok": True, "result": "Clutch sent"}

    elif cmd == "gg":
        await channel.send("🤝 GG's chat! That was a fun one! Let's run it back!")
        return {"ok": True, "result": "GG sent"}

    else:
        return JSONResponse({"ok": False, "error": f"Unknown command: {cmd}"}, status_code=400)


import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiosqlite

# Injected at runtime by main.py
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Twitch Bot Dashboard", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")


# ------------------------------------------------------------------ #
#  Pages                                                               #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ------------------------------------------------------------------ #
#  API endpoints (consumed by dashboard JS)                            #
# ------------------------------------------------------------------ #

@app.get("/api/status")
async def api_status():
    if not _bot:
        return {"live": False, "stream": None}
    monitor = _bot.stream_monitor
    stream = monitor.current_stream
    return {
        "live": monitor.is_live,
        "stream": {
            "title": stream.get("title", "") if stream else "",
            "game": stream.get("game_name", "") if stream else "",
            "viewers": stream.get("viewer_count", 0) if stream else 0,
            "thumbnail": (stream.get("thumbnail_url", "")
                          .replace("{width}", "440").replace("{height}", "248")) if stream else "",
        } if stream else None,
        "channel": _bot.cfg.channel,
    }


@app.get("/api/clips")
async def api_clips():
    if not _bot:
        return []
    clips = await _bot.helix.get_clips(_bot.cfg.broadcaster_id, first=10)
    return [{"title": c.get("title"), "url": c.get("url"), "views": c.get("view_count", 0),
             "thumbnail": c.get("thumbnail_url", "")} for c in clips]


@app.get("/api/stats")
async def api_stats():
    if not _bot:
        return {}
    db_path = _bot.cfg.stats_db
    try:
        async with aiosqlite.connect(db_path) as db:
            msg_row = await (await db.execute("SELECT COUNT(*) FROM messages")).fetchone()
            top_row = await (await db.execute(
                "SELECT username, COUNT(*) c FROM messages GROUP BY username ORDER BY c DESC LIMIT 10"
            )).fetchall()
            event_rows = await (await db.execute(
                "SELECT event_type, COUNT(*) c FROM events GROUP BY event_type ORDER BY c DESC"
            )).fetchall()
        return {
            "total_messages": msg_row[0] if msg_row else 0,
            "top_chatters": [{"user": r[0], "count": r[1]} for r in top_row],
            "events": [{"type": r[0], "count": r[1]} for r in event_rows],
        }
    except Exception:
        return {}


@app.get("/api/session_clips")
async def api_session_clips():
    if not _bot:
        return []
    return _bot.highlight_mgr._session_clips


@app.get("/api/queue")
async def api_queue():
    if not _bot:
        return []
    cog = _bot.queue_cog
    if not cog:
        return []
    return cog.queue


@app.get("/api/giveaway")
async def api_giveaway():
    if not _bot:
        return {"active": False, "entries": 0}
    cog = _bot.fun_cog
    if not cog:
        return {"active": False, "entries": 0}
    return {"active": cog.giveaway_active, "entries": cog.giveaway_entry_count}


@app.get("/api/deaths")
async def api_deaths():
    if not _bot:
        return {"count": 0}
    count = await _bot.stats.get_deaths()
    return {"count": count}


# ------------------------------------------------------------------ #
#  Voice command endpoint — called by voice_listener.py              #
# ------------------------------------------------------------------ #

@app.post("/api/voice")
async def api_voice(request: Request):
    """
    Accepts: {"command": "clip"} etc.
    Executes the action as if the broadcaster typed it.
    Returns {"ok": True, "result": "..."} or {"ok": False, "error": "..."}
    """
    if not _bot:
        return JSONResponse({"ok": False, "error": "Bot not ready"}, status_code=503)

    data = await request.json()
    cmd = data.get("command", "").strip().lower()
    arg = data.get("arg", "").strip()

    channel = _bot.get_channel(_bot.cfg.channel)
    if not channel:
        return JSONResponse({"ok": False, "error": "Channel not connected"}, status_code=503)

    if cmd == "clip":
        if not _bot.stream_monitor.is_live:
            return {"ok": False, "error": "Stream is offline"}
        if _bot.clipper._on_cooldown():
            return {"ok": False, "error": "Clip on cooldown"}
        clip = await _bot.clipper.create_clip(
            _bot.cfg.broadcaster_id, title="Voice clip", triggered_by="voice"
        )
        if clip:
            from bot.clipping.clipper import Clipper
            url = Clipper.public_url(clip)
            _bot.highlight_mgr.record_clip(clip)
            await channel.send(f"✂️ Voice clip saved! {url}")
            return {"ok": True, "result": url}
        return {"ok": False, "error": "Clip creation failed"}

    elif cmd == "death":
        count = await _bot.stats.increment_deaths()
        await channel.send(f"💀 {_bot.cfg.channel} has died {count} time(s) this stream! F in chat")
        return {"ok": True, "result": str(count)}

    elif cmd == "shoutout":
        if not arg:
            return {"ok": False, "error": "No user specified"}
        await channel.send(f"🎙️ Go check out @{arg} at https://twitch.tv/{arg} — show them some love! ❤️")
        return {"ok": True, "result": f"Shouted out {arg}"}

    elif cmd == "giveaway_start":
        cog = _bot.fun_cog
        if cog:
            cog._giveaway_active = True
            cog._giveaway_entries.clear()
            await channel.send("🎉 Giveaway started! Type !enter to participate!")
        return {"ok": True, "result": "Giveaway started"}

    elif cmd == "giveaway_draw":
        import random
        cog = _bot.fun_cog
        if cog and cog._giveaway_entries:
            winner = random.choice(list(cog._giveaway_entries))
            cog._giveaway_entries.discard(winner)
            await channel.send(f"🏆 Congratulations @{winner}! You won the giveaway! 🎉")
            return {"ok": True, "result": winner}
        return {"ok": False, "error": "No entries"}

    elif cmd == "hype":
        await channel.send(f"🔥🔥🔥 LETS GOOO! PogChamp PogChamp PogChamp 🔥🔥🔥")
        return {"ok": True, "result": "Hype sent"}

    elif cmd == "w":
        await channel.send("🏆 W IN CHAT!! Let's gooo! PogChamp 🏆")
        return {"ok": True, "result": "W sent"}

    elif cmd == "rigged":
        await channel.send("💀 RIGGED!! 2K does NOT want us to win chat 😭 the scripting is REAL")
        return {"ok": True, "result": "Rigged sent"}

    elif cmd == "clutch":
        await channel.send("🧊 ICE IN THE VEINS!! What a play! clutchPog 🔥")
        return {"ok": True, "result": "Clutch sent"}

    elif cmd == "gg":
        await channel.send("🤝 GG's chat! That was a fun one! Let's run it back!")
        return {"ok": True, "result": "GG sent"}

    else:
        return JSONResponse({"ok": False, "error": f"Unknown command: {cmd}"}, status_code=400)
