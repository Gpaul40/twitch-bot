"""
Stream schedule commands: !schedule, !setschedule, !nexstream
"""

import logging
from twitchio.ext import commands

logger = logging.getLogger("bot.schedule")


class ScheduleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._schedule: str = ""

    @commands.command(name="schedule")
    async def cmd_schedule(self, ctx: commands.Context):
        if self._schedule:
            await ctx.send(f"📅 Stream schedule: {self._schedule}")
        else:
            await ctx.send("📅 No schedule set yet! Follow on Twitch 🔔 and Twitter to never miss a stream!")

    @commands.command(name="nextstream")
    async def cmd_nextstream(self, ctx: commands.Context):
        await self.cmd_schedule(ctx)

    @commands.command(name="setschedule")
    async def cmd_setschedule(self, ctx: commands.Context, *, schedule: str = ""):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        if not schedule:
            await ctx.send("Usage: !setschedule <e.g. Mon/Wed/Fri 7PM AEST>")
            return
        self._schedule = schedule.strip()
        await ctx.send(f"📅 Schedule updated: {self._schedule}")
