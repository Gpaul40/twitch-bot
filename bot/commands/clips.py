"""
Clip commands: !clip (manual), !clips (list recent), !topclips
"""

from twitchio.ext import commands
from bot.clipping.clipper import Clipper


class ClipCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clip")
    async def cmd_clip(self, ctx: commands.Context):
        """Manually trigger a clip."""
        if not self.bot.stream_monitor.is_live:
            await ctx.send("❌ Stream is offline — can't clip right now!")
            return
        if self.bot.clipper._on_cooldown():
            await ctx.send("⏳ Clip on cooldown, try again shortly!")
            return
        clip = await self.bot.clipper.create_clip(
            self.bot.cfg.broadcaster_id, title=f"Clipped by {ctx.author.name}", triggered_by=ctx.author.name
        )
        if clip:
            url = Clipper.public_url(clip)
            self.bot.highlight_mgr.record_clip(clip)
            await ctx.send(f"✂️ Clipped by {ctx.author.name}! {url}")
            await self.bot.alerter.send_clip_alert(url, ctx.author.name)
        else:
            await ctx.send("❌ Failed to create clip. Is the stream live?")

    @commands.command(name="clips")
    async def cmd_clips(self, ctx: commands.Context):
        """Show 3 most recent clips."""
        clips = await self.bot.clipper.get_clips(self.bot.cfg.broadcaster_id, first=3)
        if not clips:
            await ctx.send("No clips found!")
            return
        lines = [f"✂️ {c['title']} — {c['url']}" for c in clips]
        await ctx.send(" | ".join(lines))

    @commands.command(name="topclips")
    async def cmd_topclips(self, ctx: commands.Context):
        """Show top 5 clips of all time."""
        clips = await self.bot.clipper.get_clips(self.bot.cfg.broadcaster_id, first=5)
        if not clips:
            await ctx.send("No clips yet!")
            return
        msg = " | ".join(f"{i+1}. {c['title']} ({c.get('view_count',0)} views)" for i, c in enumerate(clips))
        await ctx.send(f"🏆 Top Clips: {msg}")
