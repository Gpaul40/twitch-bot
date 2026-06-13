"""
Scheduled messages — posts periodic messages to chat while the stream is live.

Default messages rotate automatically. Mods can also add stream-specific
messages at runtime (they are not persisted between restarts).
"""

import asyncio
import logging

logger = logging.getLogger("bot.scheduled")

DEFAULT_MESSAGES = [
    # ── Engagement questions ───────────────────────────────────────────
    "🏀 Chat — who's your favourite NBA team? Drop it below! 👇",
    "🎮 What's your favourite game mode in 2K? MyCareer, MyTeam or Rec? Let me know!",
    "💬 Who do you think is the GOAT? Jordan or LeBron? 🐐 Drop your take in chat!",
    "🔥 Real talk — who's the best player in the game right now? Chat lemme hear it!",
    "🏆 If you could have any player on your squad IRL, who are you picking? Drop a name!",
    "📊 Rate the stream so far! 1–10 in chat — let's see the numbers 👀",
    "🎯 What build do you guys run in Rec? Let me know your setup!",
    "💭 Hot take time — drop your hottest NBA take in chat, no filter 🔥",
    "👀 Chat, what should we do next? Change the game? Squad up? Grind? You decide!",
    "🤔 Be honest chat — you think we're making the comeback or is it cooked? 😂",
    "🎮 Anyone else play 2K here? What's your overall rating at? Drop it!",
    "🏀 Predict the score! Type your prediction in chat — closest one gets a shoutout 👀",
    "💀 F in chat if you've ever rage quit a game of 2K. We've all been there 😭",
    "🔮 Chat — predict the next play. What's happening? Type it out!",
    "🎁 Drop a !lurk in chat if you're watching from the shadows 👻 we see you!",

    # ── Stream reminders ──────────────────────────────────────────────
    "✂️ See an insane play? Type clip in chat — the bot saves it automatically! 🎬",
    "💙 Enjoying the stream? Hit that follow button so you never miss a game! 🔔",
    "📺 Check out our top clips with !topclips — some highlights in there! 🔥",
    "🎵 Music requests open! Use !sr <song name> to add to the queue.",
    "📋 New here? Type !commands to see everything the bot can do!",
    "🎉 !8ball — ask it anything. It knows things you don't 👀",
    "🏅 Check your chat stats with !mystats — who's the real MVP in chat?",
    "🎰 Type !dice or !coinflip for some quick fun between plays!",
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
