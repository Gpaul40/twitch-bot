"""
Stats commands: !mystats, !topchatters
"""

from twitchio.ext import commands


class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mystats")
    async def cmd_mystats(self, ctx: commands.Context):
        count = await self.bot.stats.get_message_count(ctx.author.name)
        await ctx.send(f"📊 {ctx.author.name} has sent {count} messages in this channel!")

    @commands.command(name="topchatters")
    async def cmd_topchatters(self, ctx: commands.Context):
        top = await self.bot.stats.get_top_chatters(5)
        if not top:
            await ctx.send("No chat data yet!")
            return
        msg = " | ".join(f"{i+1}. {row[0]} ({row[1]})" for i, row in enumerate(top))
        await ctx.send(f"🏆 Top Chatters: {msg}")
