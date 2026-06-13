"""
Auto-clipping engine.
- Watches chat for trigger keywords
- Delegates all API calls to HelixClient
- Respects cooldown to avoid spam
"""

import logging
import time

logger = logging.getLogger("bot.clipper")


def _public_url(clip: dict) -> str:
    """Return the public viewable clip URL (not the editor URL)."""
    # edit_url looks like: https://clips.twitch.tv/SomeSlug/edit
    # public URL is:        https://clips.twitch.tv/SomeSlug
    edit_url = clip.get("edit_url", "")
    if edit_url.endswith("/edit"):
        return edit_url[:-5]
    return clip.get("url", edit_url)


class Clipper:
    def __init__(self, helix, cfg, stats=None):
        self.helix = helix
        self.cfg = cfg
        self.stats = stats
        self._last_clip_time: float = 0.0

    def _on_cooldown(self) -> bool:
        return (time.time() - self._last_clip_time) < self.cfg.clip_cooldown

    async def check_auto_clip_trigger(self, message, broadcaster_id: str, is_live: bool = True) -> dict | None:
        """Fires a clip if the message contains a trigger word, stream is live, and cooldown has passed."""
        if not is_live:
            return None
        words = set(message.content.strip().split())
        if words & self.cfg.clip_triggers:
            if self._on_cooldown():
                logger.debug("Clip trigger hit but on cooldown.")
                return None
            clip = await self.create_clip(broadcaster_id, title=f"Chat clip by {message.author.name}", triggered_by=message.author.name)
            if clip:
                url = _public_url(clip)
                await message.channel.send(f"✂️ Clipped! {url}")
            return clip
        return None

    async def create_clip(self, broadcaster_id: str, title: str = "", triggered_by: str = "") -> dict | None:
        """Create a clip via Helix. Returns clip dict or None."""
        clip = await self.helix.create_clip(broadcaster_id)
        if clip:
            self._last_clip_time = time.time()
            logger.info(f"Clip created: {clip['id']} | {_public_url(clip)}")
            if self.stats:
                await self.stats.record_clip(clip["id"], _public_url(clip), triggered_by or title)
        return clip

    async def get_clips(self, broadcaster_id: str, first: int = 5) -> list[dict]:
        return await self.helix.get_clips(broadcaster_id, first=first)

    @staticmethod
    def public_url(clip: dict) -> str:
        return _public_url(clip)

