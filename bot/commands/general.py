"""
General chat commands: !uptime, !so, !commands, !lurk, !game, !title
"""

import aiosqlite
from twitchio.ext import commands


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="commands")
    async def cmd_commands(self, ctx: commands.Context):
        await ctx.send(
            "📋 Commands: "
            "!clip | !clips | !topclips | "
            "!sr | !queue | !mypos | "
            "!mystats | !topchatters | "
            "!so <user> | !lurk | !game | !title | !uptime | "
            "!8ball | !dice | !coinflip | !rng | !hug | !slap | "
            "!deaths"
        )

    @commands.command(name="lurk")
    async def cmd_lurk(self, ctx: commands.Context):
        await ctx.send(f"👻 {ctx.author.name} is now lurking! Thanks for the support!")

    @commands.command(name="so")
    async def cmd_shoutout(self, ctx: commands.Context, *, user: str = ""):
        if not user:
            await ctx.send("Usage: !so <username>")
            return
        user = user.lstrip("@")
        await ctx.send(f"🎙️ Go check out @{user} at https://twitch.tv/{user} — show them some love! ❤️")

    @commands.command(name="game")
    async def cmd_game(self, ctx: commands.Context):
        info = await self.bot.helix.get_channel_info(self.bot.cfg.broadcaster_id)
        if info:
            await ctx.send(f"🎮 Currently playing: {info.get('game_name', 'Unknown')}")
        else:
            await ctx.send("Couldn't fetch game info.")

    @commands.command(name="title")
    async def cmd_title(self, ctx: commands.Context):
        info = await self.bot.helix.get_channel_info(self.bot.cfg.broadcaster_id)
        if info:
            await ctx.send(f"📺 Stream title: {info.get('title', 'Unknown')}")
        else:
            await ctx.send("Couldn't fetch title.")

    @commands.command(name="uptime")
    async def cmd_uptime(self, ctx: commands.Context):
        start = self.bot.stream_monitor._stream_start
        if not start:
            await ctx.send("Stream is currently offline.")
            return
        from datetime import datetime, timezone
        delta = datetime.now(timezone.utc) - start
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        await ctx.send(f"⏱️ Stream has been live for {h}h {m}m!")
