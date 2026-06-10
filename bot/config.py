"""
Config — loads, validates and exposes all settings.
Raises a clear error at startup if required vars are missing.
"""

import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        print(f"[CONFIG ERROR] Missing required env var: {key}")
        print("  Copy .env.example → .env and fill in your credentials.")
        sys.exit(1)
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass
class Config:
    # --- Twitch ---
    client_id: str
    client_secret: str
    oauth_token: str           # without "oauth:" prefix
    refresh_token: str
    bot_username: str
    channel: str
    broadcaster_id: str

    # --- Clipping ---
    clip_cooldown: int = 30
    clip_triggers: set = field(default_factory=lambda: {"clip", "CLIP", "!clip", "POGGERS"})
    auto_clip_on_raid: bool = True
    auto_clip_on_hype_train: bool = True

    # --- Discord ---
    discord_webhook: str = ""

    # --- Dashboard ---
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080

    # --- Stats ---
    stats_db: str = "data/stats.db"

    @classmethod
    def load(cls) -> "Config":
        raw_token = _require("TWITCH_OAUTH_TOKEN").replace("oauth:", "")
        triggers_raw = _optional("CLIP_TRIGGER_KEYWORDS", "clip,CLIP,!clip,POGGERS")
        triggers = {t.strip() for t in triggers_raw.split(",") if t.strip()}

        return cls(
            client_id=_require("TWITCH_CLIENT_ID"),
            client_secret=_require("TWITCH_CLIENT_SECRET"),
            oauth_token=raw_token,
            refresh_token=_optional("TWITCH_REFRESH_TOKEN"),
            bot_username=_require("TWITCH_BOT_USERNAME"),
            channel=_require("TWITCH_CHANNEL"),
            broadcaster_id=_require("TWITCH_BROADCASTER_ID"),
            clip_cooldown=int(_optional("CLIP_COOLDOWN_SECONDS", "30")),
            clip_triggers=triggers,
            auto_clip_on_raid=_optional("AUTO_CLIP_ON_RAID", "true").lower() == "true",
            auto_clip_on_hype_train=_optional("AUTO_CLIP_ON_HYPE_TRAIN", "true").lower() == "true",
            discord_webhook=_optional("DISCORD_WEBHOOK_URL"),
            dashboard_host=_optional("DASHBOARD_HOST", "0.0.0.0"),
            dashboard_port=int(_optional("DASHBOARD_PORT", "8080")),
            stats_db=_optional("STATS_DB_PATH", "data/stats.db"),
        )


# Singleton — import this everywhere
cfg = Config.load()
