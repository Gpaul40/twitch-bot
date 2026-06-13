"""
AI command: !ask <question>

Uses OpenAI to answer questions in Twitch chat.
Replies are trimmed to fit Twitch's 500-char message limit.
Includes a per-user cooldown to prevent spam.
"""

import logging
import time

from twitchio.ext import commands

logger = logging.getLogger("bot.commands.ai")

SYSTEM_PROMPT = (
    "You are a helpful, friendly Twitch chat assistant for the streamer {channel}. "
    "Keep all responses concise — Twitch chat messages must be under 500 characters. "
    "Be entertaining, positive and to the point. Never use markdown formatting."
)


class AICommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cooldowns: dict[str, float] = {}  # username → last use timestamp
        self._client = None

        if bot.cfg.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=bot.cfg.openai_api_key)
                logger.info(f"✅ AI enabled (model: {bot.cfg.ai_model})")
            except ImportError:
                logger.warning("openai package not installed — AI commands disabled. Run: pip install openai")
        else:
            logger.warning("OPENAI_API_KEY not set — AI commands disabled.")

    # ------------------------------------------------------------------ #
    #  !ask                                                                #
    # ------------------------------------------------------------------ #

    @commands.command(name="ask")
    async def cmd_ask(self, ctx: commands.Context, *, question: str = ""):
        if not self._client:
            await ctx.send("❌ AI is not configured. Ask the streamer to set OPENAI_API_KEY.")
            return

        if not question.strip():
            await ctx.send("💬 Usage: !ask <your question>")
            return

        # Per-user cooldown
        username = ctx.author.name.lower()
        now = time.monotonic()
        last = self._cooldowns.get(username, 0)
        if now - last < self.bot.cfg.ai_cooldown:
            remaining = int(self.bot.cfg.ai_cooldown - (now - last))
            await ctx.send(f"⏳ @{ctx.author.name} wait {remaining}s before asking again.")
            return

        self._cooldowns[username] = now

        try:
            response = await self._client.chat.completions.create(
                model=self.bot.cfg.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.format(channel=self.bot.cfg.channel),
                    },
                    {"role": "user", "content": question},
                ],
                max_tokens=120,
                temperature=0.7,
            )
            answer = response.choices[0].message.content.strip()

            # Twitch message limit is 500 chars; prefix takes ~20
            prefix = f"🤖 @{ctx.author.name}: "
            max_len = 498 - len(prefix)
            if len(answer) > max_len:
                answer = answer[:max_len - 1] + "…"

            await ctx.send(f"{prefix}{answer}")

        except Exception as exc:
            logger.error(f"OpenAI error: {exc}")
            await ctx.send(f"❌ AI error — try again in a moment.")
