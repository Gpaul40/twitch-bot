"""
Mod commands: custom commands, death counter, chat moderation, channel settings.

Mod-only: !addcmd, !delcmd, !cmds, !death, !resetdeaths,
          !slow, !slowoff, !emoteonly, !emoteonlyoff, !followonly, !followonlyoff,
          !subonly, !subonlyoff, !clear, !ban, !unban, !timeout, !untimeout
Broadcaster-only: !settitle, !setgame
Anyone: !deaths
"""

import logging
from twitchio.ext import commands

logger = logging.getLogger("bot.mod_cmds")


def _is_mod(ctx: commands.Context) -> bool:
    return ctx.author.is_mod or ctx.author.name.lower() == ctx.channel.name.lower()


def _is_broadcaster(ctx: commands.Context, bot) -> bool:
    return ctx.author.name.lower() == bot.cfg.channel.lower()


class ModCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------ #
    #  Custom commands                                                     #
    # ------------------------------------------------------------------ #

    @commands.command(name="addcmd")
    async def cmd_addcmd(self, ctx: commands.Context, *, args: str = ""):
        if not _is_mod(ctx):
            return
        parts = args.strip().split(None, 1)
        if len(parts) < 2:
            await ctx.send("Usage: !addcmd <name> <response>")
            return
        name = parts[0].lstrip("!").lower()
        response = parts[1]
        await self.bot.stats.set_custom_command(name, response)
        await ctx.send(f"✅ Command !{name} added!")

    @commands.command(name="delcmd")
    async def cmd_delcmd(self, ctx: commands.Context, *, name: str = ""):
        if not _is_mod(ctx):
            return
        name = name.strip().lstrip("!").lower()
        if not name:
            await ctx.send("Usage: !delcmd <name>")
            return
        await self.bot.stats.delete_custom_command(name)
        await ctx.send(f"🗑️ Command !{name} removed.")

    @commands.command(name="cmdlist")
    async def cmd_cmdlist(self, ctx: commands.Context):
        cmds = await self.bot.stats.get_custom_commands()
        if not cmds:
            await ctx.send("No custom commands set. Use !addcmd to create one.")
            return
        await ctx.send("📋 Custom: " + " | ".join(f"!{name}" for name in cmds))

    # ------------------------------------------------------------------ #
    #  Death counter                                                       #
    # ------------------------------------------------------------------ #

    @commands.command(name="death")
    async def cmd_death(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        count = await self.bot.stats.increment_deaths()
        await ctx.send(f"💀 {self.bot.cfg.channel} has died {count} time(s) this stream! F in chat")

    @commands.command(name="deaths")
    async def cmd_deaths(self, ctx: commands.Context):
        count = await self.bot.stats.get_deaths()
        await ctx.send(f"💀 Death count this stream: {count}")

    @commands.command(name="resetdeaths")
    async def cmd_resetdeaths(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await self.bot.stats.reset_deaths()
        await ctx.send("💀 Death counter reset to 0!")

    # ------------------------------------------------------------------ #
    #  Chat mode moderation                                                #
    # ------------------------------------------------------------------ #

    @commands.command(name="slow")
    async def cmd_slow(self, ctx: commands.Context, seconds: str = "30"):
        if not _is_mod(ctx):
            return
        try:
            s = max(0, int(seconds))
        except ValueError:
            s = 30
        await ctx.send(f"/slow {s}")

    @commands.command(name="slowoff")
    async def cmd_slowoff(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/slowoff")

    @commands.command(name="emoteonly")
    async def cmd_emoteonly(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/emoteonly")

    @commands.command(name="emoteonlyoff")
    async def cmd_emoteonlyoff(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/emoteonlyoff")

    @commands.command(name="followonly")
    async def cmd_followonly(self, ctx: commands.Context, minutes: str = "10"):
        if not _is_mod(ctx):
            return
        try:
            m = max(0, int(minutes))
        except ValueError:
            m = 10
        await ctx.send(f"/followers {m}")

    @commands.command(name="followonlyoff")
    async def cmd_followonlyoff(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/followersoff")

    @commands.command(name="subonly")
    async def cmd_subonly(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/subscribers")

    @commands.command(name="subonlyoff")
    async def cmd_subonlyoff(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/subscribersoff")

    @commands.command(name="clearchat")
    async def cmd_clear(self, ctx: commands.Context):
        if not _is_mod(ctx):
            return
        await ctx.send("/clear")

    @commands.command(name="ban")
    async def cmd_ban(self, ctx: commands.Context, user: str = "", *, reason: str = ""):
        if not _is_mod(ctx):
            return
        if not user:
            await ctx.send("Usage: !ban <user> [reason]")
            return
        user = user.lstrip("@")
        msg = f"/ban {user}" + (f" {reason}" if reason else "")
        await ctx.send(msg)

    @commands.command(name="unban")
    async def cmd_unban(self, ctx: commands.Context, user: str = ""):
        if not _is_mod(ctx):
            return
        if not user:
            await ctx.send("Usage: !unban <user>")
            return
        await ctx.send(f"/unban {user.lstrip('@')}")

    @commands.command(name="timeout")
    async def cmd_timeout(
        self, ctx: commands.Context, user: str = "", duration: str = "600", *, reason: str = ""
    ):
        if not _is_mod(ctx):
            return
        if not user:
            await ctx.send("Usage: !timeout <user> [seconds] [reason]")
            return
        user = user.lstrip("@")
        try:
            d = int(duration)
        except ValueError:
            # duration might be text (part of reason), treat as default
            reason = f"{duration} {reason}".strip()
            d = 600
        msg = f"/timeout {user} {d}" + (f" {reason}" if reason else "")
        await ctx.send(msg)

    @commands.command(name="untimeout")
    async def cmd_untimeout(self, ctx: commands.Context, user: str = ""):
        if not _is_mod(ctx):
            return
        if not user:
            await ctx.send("Usage: !untimeout <user>")
            return
        await ctx.send(f"/untimeout {user.lstrip('@')}")

    # ------------------------------------------------------------------ #
    #  Channel settings (broadcaster only via Helix API)                  #
    # ------------------------------------------------------------------ #

    @commands.command(name="settitle")
    async def cmd_settitle(self, ctx: commands.Context, *, title: str = ""):
        if not _is_broadcaster(ctx, self.bot):
            await ctx.send("Only the broadcaster can change the title.")
            return
        if not title:
            await ctx.send("Usage: !settitle <new title>")
            return
        success = await self.bot.helix.update_channel(self.bot.cfg.broadcaster_id, title=title)
        if success:
            await ctx.send(f"✅ Title updated to: {title}")
        else:
            await ctx.send("❌ Failed to update title. Check bot permissions (channel:manage:broadcast scope).")

    @commands.command(name="setgame")
    async def cmd_setgame(self, ctx: commands.Context, *, game: str = ""):
        if not _is_broadcaster(ctx, self.bot):
            await ctx.send("Only the broadcaster can change the game.")
            return
        if not game:
            await ctx.send("Usage: !setgame <game name>")
            return
        game_data = await self.bot.helix.get_game_by_name(game)
        if not game_data:
            await ctx.send(f"❌ Game '{game}' not found on Twitch.")
            return
        success = await self.bot.helix.update_channel(
            self.bot.cfg.broadcaster_id, game_id=game_data["id"]
        )
        if success:
            await ctx.send(f"✅ Game set to: {game_data['name']}")
        else:
            await ctx.send("❌ Failed to update game. Check bot permissions.")
