"""
Song/viewer request queue.

Commands:
  !sr <song>       — add or update your request
  !queue           — show the current queue (top 5)
  !nextq           — mod: pop and announce next song
  !clearq          — mod: wipe the whole queue
  !removeq <pos>   — mod: remove a specific position
  !mypos           — check your position in the queue
"""

import logging
from twitchio.ext import commands

logger = logging.getLogger("bot.queue")


def _is_mod_or_broadcaster(ctx: commands.Context, bot) -> bool:
    return ctx.author.is_mod or ctx.author.name.lower() == bot.cfg.channel.lower()


class QueueCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._queue: list[dict] = []  # [{"user": str, "request": str}]

    # ------------------------------------------------------------------ #
    #  Commands                                                            #
    # ------------------------------------------------------------------ #

    @commands.command(name="sr")
    async def cmd_sr(self, ctx: commands.Context, *, request: str = ""):
        if not request:
            await ctx.send("🎵 Usage: !sr <song name or YouTube link>")
            return
        existing = next(
            (i for i, r in enumerate(self._queue) if r["user"] == ctx.author.name), None
        )
        entry = {"user": ctx.author.name, "request": request}
        if existing is not None:
            self._queue[existing] = entry
            await ctx.send(
                f"🎵 @{ctx.author.name} updated request to: {request} (position {existing + 1})"
            )
        else:
            self._queue.append(entry)
            await ctx.send(
                f"🎵 @{ctx.author.name} added to queue at position {len(self._queue)}: {request}"
            )

    @commands.command(name="queue")
    async def cmd_queue(self, ctx: commands.Context):
        if not self._queue:
            await ctx.send("📭 Queue is empty! Add a song with !sr <song>")
            return
        items = self._queue[:5]
        msg = " | ".join(f"{i + 1}. {r['user']}: {r['request']}" for i, r in enumerate(items))
        extra = len(self._queue) - 5
        if extra > 0:
            msg += f" (+{extra} more)"
        await ctx.send(f"🎵 Queue ({len(self._queue)} total): {msg}")

    @commands.command(name="nextq")
    async def cmd_nextq(self, ctx: commands.Context):
        if not _is_mod_or_broadcaster(ctx, self.bot):
            return
        if not self._queue:
            await ctx.send("📭 Queue is empty!")
            return
        nxt = self._queue.pop(0)
        await ctx.send(
            f"▶️ Now playing: \"{nxt['request']}\" requested by @{nxt['user']} "
            f"— {len(self._queue)} left in queue"
        )

    @commands.command(name="clearq")
    async def cmd_clearq(self, ctx: commands.Context):
        if not _is_mod_or_broadcaster(ctx, self.bot):
            return
        count = len(self._queue)
        self._queue.clear()
        await ctx.send(f"🗑️ Queue cleared! ({count} entries removed)")

    @commands.command(name="removeq")
    async def cmd_removeq(self, ctx: commands.Context, pos: str = ""):
        if not _is_mod_or_broadcaster(ctx, self.bot):
            return
        try:
            idx = int(pos) - 1
        except (ValueError, TypeError):
            await ctx.send("Usage: !removeq <position number>")
            return
        if 0 <= idx < len(self._queue):
            removed = self._queue.pop(idx)
            await ctx.send(f"🗑️ Removed position {idx + 1}: \"{removed['request']}\" by @{removed['user']}")
        else:
            await ctx.send(f"❌ No entry at position {pos}. Queue has {len(self._queue)} items.")

    @commands.command(name="mypos")
    async def cmd_mypos(self, ctx: commands.Context):
        idx = next(
            (i for i, r in enumerate(self._queue) if r["user"] == ctx.author.name), None
        )
        if idx is None:
            await ctx.send(
                f"@{ctx.author.name} — you're not in the queue. Use !sr <song> to add!"
            )
        else:
            await ctx.send(
                f"@{ctx.author.name} — you're at position {idx + 1}: \"{self._queue[idx]['request']}\""
            )

    # ------------------------------------------------------------------ #
    #  Exposed for dashboard                                               #
    # ------------------------------------------------------------------ #

    @property
    def queue(self) -> list[dict]:
        return list(self._queue)
