"""
FastAPI dashboard — live stats, recent clips, stream status.
Runs alongside the bot on port 8080 (configurable).
"""

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
