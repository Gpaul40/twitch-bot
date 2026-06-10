"""
General chat commands: !uptime, !so, !commands, !lurk
"""

from twitchio.ext import commands


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="commands")
    async def cmd_commands(self, ctx: commands.Context):
        await ctx.send(
            "📋 Commands: !clip | !clips | !mystats | !topchatters | !so <user> | !lurk | !uptime"
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
        await ctx.send(
            f"🎙️ Shoutout to @{user}! Go check them out at https://twitch.tv/{user} ❤️"
        )

    @commands.command(name="uptime")
    async def cmd_uptime(self, ctx: commands.Context):
        # Requires stream start time from Helix — placeholder for now
        await ctx.send("⏱️ Uptime tracking coming soon!")
