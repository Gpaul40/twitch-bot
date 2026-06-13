"""
Points commands: !points, !toppoints, !redeem, !addreward, !rewards
"""

import logging
from twitchio.ext import commands
from bot.loyalty import POINTS_PER_MESSAGE, POINTS_PER_SUB

logger = logging.getLogger("bot.commands.points")


class PointsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="points")
    async def cmd_points(self, ctx: commands.Context):
        if not hasattr(self.bot, 'loyalty'):
            return
        bal = await self.bot.loyalty.get_points(ctx.author.name)
        await ctx.send(f"💰 @{ctx.author.name} — you have {bal:,} points! Earn more by chatting and watching 🎮")

    @commands.command(name="toppoints")
    async def cmd_toppoints(self, ctx: commands.Context):
        if not hasattr(self.bot, 'loyalty'):
            return
        top = await self.bot.loyalty.get_top(5)
        if not top:
            await ctx.send("No points data yet!")
            return
        msg = " | ".join(f"{i+1}. {r[0]} ({r[1]:,})" for i, r in enumerate(top))
        await ctx.send(f"💰 Top Points: {msg}")

    @commands.command(name="rewards")
    async def cmd_rewards(self, ctx: commands.Context):
        if not hasattr(self.bot, 'loyalty'):
            return
        rewards = await self.bot.loyalty.get_rewards()
        if not rewards:
            await ctx.send("No rewards set up yet. Ask the streamer to add some with !addreward!")
            return
        msg = " | ".join(f"{r[0]} ({r[1]:,}pts)" for r in rewards)
        await ctx.send(f"🎁 Rewards: {msg} — Use !redeem <name> to redeem!")

    @commands.command(name="redeem")
    async def cmd_redeem(self, ctx: commands.Context, *, item: str = ""):
        if not hasattr(self.bot, 'loyalty') or not item:
            await ctx.send("Usage: !redeem <reward name> — see !rewards for options")
            return
        reward = await self.bot.loyalty.get_reward(item.lower().strip())
        if not reward:
            await ctx.send(f"❌ Reward '{item}' not found. Type !rewards to see what's available.")
            return
        name, cost, desc = reward
        success = await self.bot.loyalty.deduct_points(ctx.author.name, cost)
        if not success:
            bal = await self.bot.loyalty.get_points(ctx.author.name)
            await ctx.send(f"❌ @{ctx.author.name} — not enough points! You have {bal:,}, need {cost:,}.")
        else:
            channel = self.bot.get_channel(self.bot.cfg.channel)
            await ctx.send(f"🎁 @{ctx.author.name} redeemed: {name}! {desc} 🎉")
            logger.info(f"{ctx.author.name} redeemed {name} for {cost} points")

    @commands.command(name="addreward")
    async def cmd_addreward(self, ctx: commands.Context, *, args: str = ""):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 2:
            await ctx.send("Usage: !addreward <name> | <cost> | <description>")
            return
        try:
            name = parts[0].lower()
            cost = int(parts[1])
            desc = parts[2] if len(parts) > 2 else ""
            await self.bot.loyalty.add_reward(name, cost, desc)
            await ctx.send(f"✅ Reward added: !redeem {name} ({cost:,} points) — {desc}")
        except (ValueError, IndexError):
            await ctx.send("Usage: !addreward <name> | <cost> | <description>")

    @commands.command(name="givepts")
    async def cmd_givepts(self, ctx: commands.Context, user: str = "", amount: str = "0"):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        user = user.lstrip("@")
        try:
            amt = int(amount)
        except ValueError:
            await ctx.send("Usage: !givepts <user> <amount>")
            return
        if not hasattr(self.bot, 'loyalty') or not user or amt <= 0:
            return
        await self.bot.loyalty.add_points(user, amt, reason="mod gift")
        await ctx.send(f"💰 @{user} was given {amt:,} points by {ctx.author.name}!")
