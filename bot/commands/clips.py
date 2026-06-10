"""
Clip commands: !clip (manual), !clips (list recent)
"""

from twitchio.ext import commands


class ClipCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clip")
    async def cmd_clip(self, ctx: commands.Context):
        """Manually trigger a clip."""
        if self.bot.clipper._on_cooldown():
            await ctx.send(f"⏳ Clip on cooldown, try again shortly!")
            return
        clip_url = await self.bot.clipper.create_clip(
            self.bot.broadcaster_id, title=f"Clipped by {ctx.author.name}"
        )
        if clip_url:
            await ctx.send(f"✂️ Clipped by {ctx.author.name}! {clip_url}")
            await self.bot.alerter.send_clip_alert(clip_url, ctx.author.name)
        else:
            await ctx.send("❌ Failed to create clip. Is the stream live?")

    @commands.command(name="clips")
    async def cmd_clips(self, ctx: commands.Context):
        """Show the 3 most recent clips."""
        clips = await self.bot.clipper.get_clips(self.bot.broadcaster_id, first=3)
        if not clips:
            await ctx.send("No clips found!")
            return
        lines = [f"✂️ {c['title']} — {c['url']}" for c in clips]
        await ctx.send(" | ".join(lines))
