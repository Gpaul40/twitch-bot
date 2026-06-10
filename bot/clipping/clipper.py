"""
Auto-clipping engine.
- Watches chat for trigger keywords
- Delegates all API calls to HelixClient
- Respects cooldown to avoid spam
"""

import logging
import time

logger = logging.getLogger("bot.clipper")


class Clipper:
    def __init__(self, helix, cfg):
        self.helix = helix
        self.cfg = cfg
        self._last_clip_time: float = 0.0

    def _on_cooldown(self) -> bool:
        return (time.time() - self._last_clip_time) < self.cfg.clip_cooldown

    async def check_auto_clip_trigger(self, message, broadcaster_id: str) -> dict | None:
        """Fires a clip if the message contains a trigger word and cooldown has passed."""
        words = set(message.content.strip().split())
        if words & self.cfg.clip_triggers:
            if self._on_cooldown():
                logger.debug("Clip trigger hit but on cooldown.")
                return None
            clip = await self.create_clip(broadcaster_id, title=f"Chat clip by {message.author.name}")
            if clip:
                await message.channel.send(f"✂️ Clipped! {clip['edit_url']}")
            return clip
        return None

    async def create_clip(self, broadcaster_id: str, title: str = "") -> dict | None:
        """Create a clip via Helix. Returns clip dict or None."""
        clip = await self.helix.create_clip(broadcaster_id)
        if clip:
            self._last_clip_time = time.time()
            logger.info(f"Clip created: {clip['id']} | {clip['edit_url']}")
        return clip

    async def get_clips(self, broadcaster_id: str, first: int = 5) -> list[dict]:
        return await self.helix.get_clips(broadcaster_id, first=first)

