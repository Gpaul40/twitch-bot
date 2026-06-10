"""
Highlight manager.

Twitch's API doesn't expose a direct 'create highlight' endpoint (it requires
the Twitch video editor). This module:
  1. Tracks clips created during a stream session.
  2. After stream ends, ranks them by view count.
  3. Logs the top candidates and posts them to Discord so you can
     promote them to highlights in the Twitch dashboard with one click.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("bot.highlights")

DASHBOARD_VIDEOS_URL = "https://dashboard.twitch.tv/videos"


class HighlightManager:
    def __init__(self, helix, alerter, stats):
        self.helix = helix
        self.alerter = alerter
        self.stats = stats
        self._session_clips: list[dict] = []

    def record_clip(self, clip: dict):
        """Call this whenever a clip is created during a stream."""
        self._session_clips.append({**clip, "recorded_at": datetime.now(timezone.utc).isoformat()})

    def reset_session(self):
        self._session_clips.clear()

    async def process_end_of_stream(self, broadcaster_id: str):
        """
        Called when stream goes offline.
        Fetches clip stats, picks the best ones, and posts a Discord summary.
        """
        if not self._session_clips:
            logger.info("No clips recorded this session.")
            return

        # Re-fetch clips to get updated view counts
        enriched = []
        for c in self._session_clips:
            fresh = await self.helix.get_clip(c["id"])
            if fresh:
                enriched.append(fresh)
            else:
                enriched.append(c)

        enriched.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        top = enriched[:5]

        logger.info(f"=== {len(enriched)} clips this session. Top {len(top)}: ===")
        for i, clip in enumerate(top, 1):
            logger.info(f"  {i}. {clip.get('title', 'Untitled')} | {clip.get('view_count', 0)} views | {clip.get('url', '')}")

        await self.alerter.send_highlight_candidates(top, DASHBOARD_VIDEOS_URL)
        await self.stats.record_event("highlight_candidates", extra=str(len(top)))
        self.reset_session()
