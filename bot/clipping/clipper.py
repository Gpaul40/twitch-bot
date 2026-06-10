"""
Auto-clipping engine.
- Watches chat for trigger keywords
- Creates clips via Twitch API
- Respects cooldown to avoid spam
"""

import os
import time
import logging
import aiohttp

logger = logging.getLogger("bot.clipper")

HELIX_CLIPS_URL = "https://api.twitch.tv/helix/clips"


class Clipper:
    def __init__(self, client_id: str, oauth_token: str):
        self.client_id = client_id
        self.oauth_token = oauth_token
        self.cooldown = int(os.getenv("CLIP_COOLDOWN_SECONDS", "30"))
        self.triggers = set(
            kw.strip() for kw in os.getenv("CLIP_TRIGGER_KEYWORDS", "clip,CLIP,!clip").split(",")
        )
        self._last_clip_time: float = 0.0

    @property
    def _headers(self) -> dict:
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.oauth_token}",
        }

    def _on_cooldown(self) -> bool:
        return (time.time() - self._last_clip_time) < self.cooldown

    async def check_auto_clip_trigger(self, message, broadcaster_id: str):
        """Check if message contains a clip keyword and fire if not on cooldown."""
        words = set(message.content.strip().split())
        if words & self.triggers:
            if self._on_cooldown():
                logger.debug("Clip trigger hit but on cooldown.")
                return
            clip_url = await self.create_clip(broadcaster_id)
            if clip_url:
                await message.channel.send(f"✂️ Clipped! {clip_url}")

    async def create_clip(self, broadcaster_id: str, title: str = "") -> str | None:
        """Call Twitch Helix API to create a clip. Returns the clip edit URL."""
        params = {"broadcaster_id": broadcaster_id}
        async with aiohttp.ClientSession() as session:
            async with session.post(HELIX_CLIPS_URL, headers=self._headers, params=params) as resp:
                if resp.status == 202:
                    data = await resp.json()
                    clip_id = data["data"][0]["id"]
                    edit_url = data["data"][0]["edit_url"]
                    self._last_clip_time = time.time()
                    logger.info(f"Clip created: {clip_id} | {edit_url}")
                    return edit_url
                else:
                    text = await resp.text()
                    logger.error(f"Clip failed [{resp.status}]: {text}")
                    return None

    async def get_clips(self, broadcaster_id: str, first: int = 5) -> list[dict]:
        """Fetch the most recent clips for a broadcaster."""
        params = {"broadcaster_id": broadcaster_id, "first": str(first)}
        async with aiohttp.ClientSession() as session:
            async with session.get(HELIX_CLIPS_URL, headers=self._headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                logger.error(f"get_clips failed [{resp.status}]")
                return []
