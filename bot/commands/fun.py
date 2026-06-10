"""
Fun commands: !8ball, !dice, !coinflip, !rng, !hug, !slap, !giveaway, !enter
"""

import random
from twitchio.ext import commands

EIGHT_BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]


class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._giveaway_active: bool = False
        self._giveaway_entries: set[str] = set()

    # ------------------------------------------------------------------ #
    #  Random / games                                                      #
    # ------------------------------------------------------------------ #

    @commands.command(name="8ball")
    async def cmd_8ball(self, ctx: commands.Context, *, question: str = ""):
        if not question:
            await ctx.send("🎱 Ask me something! Usage: !8ball <question>")
            return
        await ctx.send(f"🎱 {random.choice(EIGHT_BALL_RESPONSES)}")

    @commands.command(name="dice")
    async def cmd_dice(self, ctx: commands.Context, sides: str = "6"):
        try:
            n = max(2, min(int(sides), 1000))
        except ValueError:
            n = 6
        await ctx.send(f"🎲 {ctx.author.name} rolled a d{n} and got {random.randint(1, n)}!")

    @commands.command(name="coinflip")
    async def cmd_coinflip(self, ctx: commands.Context):
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        await ctx.send(f"🪙 {ctx.author.name} flipped: {result}!")

    @commands.command(name="rng")
    async def cmd_rng(self, ctx: commands.Context, *, args: str = ""):
        parts = args.strip().split()
        try:
            if len(parts) == 2:
                lo, hi = int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                lo, hi = 1, int(parts[0])
            else:
                lo, hi = 1, 100
        except ValueError:
            lo, hi = 1, 100
        if lo > hi:
            lo, hi = hi, lo
        await ctx.send(f"🎰 {ctx.author.name}: {random.randint(lo, hi)} (range {lo}–{hi})")

    # ------------------------------------------------------------------ #
    #  Social                                                              #
    # ------------------------------------------------------------------ #

    @commands.command(name="hug")
    async def cmd_hug(self, ctx: commands.Context, *, target: str = ""):
        target = target.lstrip("@").strip() or "everyone"
        await ctx.send(f"🤗 {ctx.author.name} gives {target} a big hug! ❤️")

    @commands.command(name="slap")
    async def cmd_slap(self, ctx: commands.Context, *, target: str = ""):
        target = target.lstrip("@").strip() or "the air"
        await ctx.send(f"👋 {ctx.author.name} slaps {target} with a large trout!")

    # ------------------------------------------------------------------ #
    #  Giveaway                                                            #
    # ------------------------------------------------------------------ #

    @commands.command(name="giveaway")
    async def cmd_giveaway(self, ctx: commands.Context, *, action: str = ""):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        action = action.lower().strip()
        if action == "start":
            self._giveaway_active = True
            self._giveaway_entries.clear()
            await ctx.send("🎉 Giveaway started! Type !enter to participate!")
        elif action == "end":
            self._giveaway_active = False
            await ctx.send(
                f"🎉 Giveaway closed! {len(self._giveaway_entries)} entries. "
                "Use !giveaway draw to pick a winner!"
            )
        elif action == "draw":
            if not self._giveaway_entries:
                await ctx.send("❌ No entries in the giveaway!")
                return
            winner = random.choice(list(self._giveaway_entries))
            self._giveaway_entries.discard(winner)
            await ctx.send(f"🏆 Congratulations @{winner}! You won the giveaway! 🎉")
        elif action == "cancel":
            self._giveaway_active = False
            self._giveaway_entries.clear()
            await ctx.send("❌ Giveaway cancelled.")
        else:
            await ctx.send("Usage: !giveaway start | end | draw | cancel")

    @commands.command(name="enter")
    async def cmd_enter(self, ctx: commands.Context):
        if not self._giveaway_active:
            return
        self._giveaway_entries.add(ctx.author.name)
        await ctx.send(
            f"✅ {ctx.author.name} entered the giveaway! "
            f"({len(self._giveaway_entries)} total entries)"
        )

    # ------------------------------------------------------------------ #
    #  Exposed for dashboard / other modules                              #
    # ------------------------------------------------------------------ #

    @property
    def giveaway_active(self) -> bool:
        return self._giveaway_active

    @property
    def giveaway_entry_count(self) -> int:
        return len(self._giveaway_entries)
