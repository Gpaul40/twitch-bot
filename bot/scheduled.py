"""
Scheduled messages — posts periodic messages to chat while the stream is live.

Default messages rotate automatically. Mods can also add stream-specific
messages at runtime (they are not persisted between restarts).
"""

import asyncio
import logging

logger = logging.getLogger("bot.scheduled")

DEFAULT_MESSAGES = [
    "📋 Check out all bot commands: !commands | !clips | !sr | !8ball | !coinflip | !dice | !hug",
    "✂️ See an epic moment? Type !clip in chat to save it!",
    "💙 Enjoying the stream? Hit that Follow button so you never miss a stream! 🔔",
    "🎉 Want to enter a giveaway when one is running? Watch for !giveaway start announcements!",
    "📺 Check out our top clips with !topclips — some highlights in there! 🔥",
    "🎵 Song requests are open! Use !sr <song name> to add your song to the queue.",
]


class ScheduledMessages:
    def __init__(self, bot, interval_seconds: int = 1800):
        self.bot = bot
        self.interval = interval_seconds
        self._messages: list[str] = list(DEFAULT_MESSAGES)
        self._index: int = 0
        self._task: asyncio.Task | None = None

    def add_message(self, msg: str):
        """Add a message to the rotation (runtime only, not persisted)."""
        self._messages.append(msg)

    def remove_message(self, idx: int):
        """Remove a message by 0-based index."""
        if 0 <= idx < len(self._messages):
            self._messages.pop(idx)

    def start(self):
        self._task = asyncio.create_task(self._loop(), name="scheduled-messages")
        logger.info(f"Scheduled messages started (every {self.interval}s)")

    def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await asyncio.sleep(self.interval)
                if self.bot.stream_monitor.is_live:
                    await self._post_next()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(f"Scheduled message error: {exc}")

    async def _post_next(self):
        if not self._messages:
            return
        msg = self._messages[self._index % len(self._messages)]
        self._index += 1
        channel = self.bot.get_channel(self.bot.cfg.channel)
        if channel:
            await channel.send(msg)
            logger.debug(f"Scheduled message sent: {msg[:60]}")
