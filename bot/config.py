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

    # --- Automation ---
    welcome_new_chatters: bool = True
    auto_so_on_raid: bool = True
    scheduled_msg_interval: int = 1800  # seconds between periodic messages

    # --- Discord ---
    discord_webhook: str = ""

    # --- Twitter/X ---
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""
    auto_tweet_live: bool = True
    auto_tweet_clips: bool = True

    # --- Auto-raid out ---
    auto_raid_out: bool = True
    raid_targets: list = field(default_factory=list)

    # --- Dashboard ---
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080

    # --- Stats ---
    stats_db: str = "data/stats.db"

    # --- AI ---
    openai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_cooldown: int = 10

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
            welcome_new_chatters=_optional("WELCOME_NEW_CHATTERS", "true").lower() == "true",
            auto_so_on_raid=_optional("AUTO_SO_ON_RAID", "true").lower() == "true",
            scheduled_msg_interval=int(_optional("SCHEDULED_MSG_INTERVAL", "1800")),
            discord_webhook=_optional("DISCORD_WEBHOOK_URL"),
            twitter_api_key=_optional("TWITTER_API_KEY"),
            twitter_api_secret=_optional("TWITTER_API_SECRET"),
            twitter_access_token=_optional("TWITTER_ACCESS_TOKEN"),
            twitter_access_secret=_optional("TWITTER_ACCESS_SECRET"),
            auto_tweet_live=_optional("AUTO_TWEET_LIVE", "true").lower() == "true",
            auto_tweet_clips=_optional("AUTO_TWEET_CLIPS", "true").lower() == "true",
            auto_raid_out=_optional("AUTO_RAID_OUT", "true").lower() == "true",
            raid_targets=[t.strip() for t in _optional("RAID_TARGETS", "").split(",") if t.strip()],
            dashboard_host=_optional("DASHBOARD_HOST", "0.0.0.0"),
            dashboard_port=int(_optional("DASHBOARD_PORT", "8080")),
            stats_db=_optional("STATS_DB_PATH", "data/stats.db"),
            openai_api_key=_optional("OPENAI_API_KEY"),
            ai_model=_optional("AI_MODEL", "gpt-4o-mini"),
            ai_cooldown=int(_optional("AI_COOLDOWN_SECONDS", "10")),
        )


# Singleton — import this everywhere
cfg = Config.load()
