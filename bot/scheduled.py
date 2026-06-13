"""
Scheduled messages — posts periodic messages to chat while the stream is live.

Default messages rotate automatically. Mods can also add stream-specific
messages at runtime (they are not persisted between restarts).
"""

import asyncio
import logging

logger = logging.getLogger("bot.scheduled")

DEFAULT_MESSAGES = [
    "🏀 Type !clip if you see an insane play — let's save the highlights!",
    "💙 Enjoying the stream? Drop a follow so you never miss a game! 🔔",
    "🎮 What team are you rolling with in NBA 2K? Let me know in chat!",
    "✂️ See a crazy dunk or play? Type clip in chat and the bot will save it!",
    "📊 Wanna see your chat stats? Type !mystats — who's the real MVP of chat?",
    "🏆 Check out our best clips with !topclips — some highlight reels in there!",
    "🎵 Song requests open! Use !sr <song name> to add to the queue.",
    "🎯 !8ball — ask the bot anything, it knows all 👀",
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
