"""
Stream Monitor — background async task.

Polls Helix every 30 seconds to detect:
  - Stream going live   → Discord alert + record session start
  - Stream going offline → record session end + trigger highlight suggestions
  - Hype train active   → auto-clip if enabled
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("bot.stream_monitor")

POLL_INTERVAL = 30  # seconds


class StreamMonitor:
    def __init__(self, helix, stats, alerter, clipper, highlight_mgr, cfg, twitter=None, auto_raider=None):
        self.helix = helix
        self.stats = stats
        self.alerter = alerter
        self.clipper = clipper
        self.highlight_mgr = highlight_mgr
        self.cfg = cfg
        self.twitter = twitter
        self.auto_raider = auto_raider

        self._live: bool = False
        self._stream_start: datetime | None = None
        self._hype_train_active: bool = False
        self._task: asyncio.Task | None = None

        # Exposed for dashboard
        self.current_stream: dict | None = None

    def start(self):
        self._task = asyncio.create_task(self._loop(), name="stream-monitor")
        logger.info("Stream monitor started.")

    def stop(self):
        if self._task:
            self._task.cancel()

    @property
    def is_live(self) -> bool:
        return self._live

    async def _loop(self):
        while True:
            try:
                await self._poll()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(f"Stream monitor error: {exc}")
            await asyncio.sleep(POLL_INTERVAL)

    async def _poll(self):
        stream = await self.helix.get_stream(self.cfg.broadcaster_id)

        if stream and not self._live:
            await self._on_go_live(stream)

        elif not stream and self._live:
            await self._on_go_offline()

        self.current_stream = stream

        # Hype train check
        if self._live and self.cfg.auto_clip_on_hype_train:
            await self._check_hype_train()

    async def _on_go_live(self, stream: dict):
        self._live = True
        self._stream_start = datetime.now(timezone.utc)
        title = stream.get("title", "")
        game = stream.get("game_name", "")
        logger.info(f"Stream LIVE — {title} | {game}")
        await self.stats.record_event("go_live", extra=f"{title} | {game}")
        await self.alerter.send_live_alert(self.cfg.channel, title, game)
        if self.twitter:
            await self.twitter.post_go_live(self.cfg.channel, title, game)

    async def _on_go_offline(self):
        self._live = False
        duration = ""
        if self._stream_start:
            delta = datetime.now(timezone.utc) - self._stream_start
            h, rem = divmod(int(delta.total_seconds()), 3600)
            m = rem // 60
            duration = f"{h}h {m}m"
        logger.info(f"Stream OFFLINE. Duration: {duration}")
        await self.stats.record_event("go_offline", extra=duration)
        await self.alerter.send_offline_alert(self.cfg.channel, duration)
        self._stream_start = None

        # Twitter end-of-stream recap
        clip_count = len(self.highlight_mgr._session_clips)
        if self.twitter:
            await self.twitter.post_go_offline(self.cfg.channel, duration, clip_count)

        # Auto-raid out
        game = self.current_stream.get("game_name", "") if self.current_stream else ""
        self.current_stream = None
        if self.auto_raider:
            await self.auto_raider.raid_out(current_game_name=game)

        # Suggest highlights
        await self._suggest_highlights()
        await self.highlight_mgr.process_end_of_stream(self.cfg.broadcaster_id)

    async def _check_hype_train(self):
        hype = await self.helix.get_hype_train(self.cfg.broadcaster_id)
        if hype and not self._hype_train_active:
            self._hype_train_active = True
            logger.info("Hype train detected — auto-clipping!")
            clip = await self.clipper.create_clip(self.cfg.broadcaster_id, title="Hype Train 🚂")
            if clip:
                await self.alerter.send_clip_alert(clip["edit_url"], triggered_by="Hype Train")
        elif not hype:
            self._hype_train_active = False

    async def _suggest_highlights(self):
        """After stream ends, log the top clips as highlight candidates."""
        clips = await self.helix.get_clips(self.cfg.broadcaster_id, first=5)
        if clips:
            logger.info("=== Top clips from this stream (highlight candidates) ===")
            for i, clip in enumerate(clips, 1):
                logger.info(f"  {i}. {clip.get('title', 'Untitled')} — {clip.get('url', '')}")
            logger.info("Visit https://dashboard.twitch.tv/videos to promote to highlights.")
