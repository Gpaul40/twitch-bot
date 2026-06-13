"""
Chat games: !trivia, !predict, !poll

!trivia          — NBA trivia question (mod can also use !trivia start)
!predict <score> — Predict final score, bot announces closest at end
!poll <question> | opt1 | opt2 | opt3  — Run a chat vote
!endpoll         — Mod: close poll and show results
"""

import asyncio
import random
import logging
from twitchio.ext import commands

logger = logging.getLogger("bot.chat_games")

NBA_TRIVIA = [
    ("How many NBA championships did Michael Jordan win?", "6"),
    ("Who holds the record for most points in a single NBA game?", "Wilt Chamberlain (100)"),
    ("Which team has won the most NBA championships?", "Boston Celtics (17)"),
    ("Who was the first overall pick in the 2003 NBA Draft?", "LeBron James"),
    ("What year did the Golden State Warriors set the record for best regular season record?", "2016 (73-9)"),
    ("Which player is known as 'The Mailman'?", "Karl Malone"),
    ("Who scored 81 points in a single game in 2006?", "Kobe Bryant"),
    ("What team did LeBron James win his first championship with?", "Miami Heat"),
    ("Which player won the most NBA MVP awards?", "Kareem Abdul-Jabbar (6)"),
    ("What does NBA stand for?", "National Basketball Association"),
    ("Who is the all-time NBA scoring leader?", "LeBron James"),
    ("Which player's nickname is 'The Greek Freak'?", "Giannis Antetokounmpo"),
    ("How long is an NBA quarter?", "12 minutes"),
    ("What team did Kobe Bryant play his entire career with?", "Los Angeles Lakers"),
    ("Who was the first player to win Finals MVP with two different teams?", "LeBron James"),
]


class ChatGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._trivia_active: bool = False
        self._trivia_answer: str = ""
        self._trivia_task: asyncio.Task | None = None
        self._predictions: dict[str, str] = {}  # username → predicted score
        self._predictions_open: bool = False
        self._poll_question: str = ""
        self._poll_options: list[str] = []
        self._poll_votes: dict[str, int] = {}  # username → option index
        self._poll_active: bool = False

    # ------------------------------------------------------------------ #
    #  Trivia                                                              #
    # ------------------------------------------------------------------ #

    @commands.command(name="trivia")
    async def cmd_trivia(self, ctx: commands.Context):
        if self._trivia_active:
            await ctx.send(f"🎯 Trivia already running! Answer: {self._trivia_answer[:1]}{'*' * (len(self._trivia_answer)-1)}")
            return
        q, a = random.choice(NBA_TRIVIA)
        self._trivia_active = True
        self._trivia_answer = a.lower()
        await ctx.send(f"🏀 NBA TRIVIA: {q} (30 seconds!)")
        self._trivia_task = asyncio.create_task(self._trivia_timeout(ctx.channel))

    async def _trivia_timeout(self, channel):
        await asyncio.sleep(30)
        if self._trivia_active:
            self._trivia_active = False
            await channel.send(f"⏰ Time's up! The answer was: {self._trivia_answer.title()} 🏀")

    async def event_message(self, message):
        """Called from core — check trivia answers."""
        if not self._trivia_active or message.echo:
            return
        if self._trivia_answer in message.content.lower():
            self._trivia_active = False
            if self._trivia_task:
                self._trivia_task.cancel()
            await message.channel.send(
                f"🎉 @{message.author.name} got it! The answer was: {self._trivia_answer.title()} 🏆"
            )

    # ------------------------------------------------------------------ #
    #  Score predictions                                                   #
    # ------------------------------------------------------------------ #

    @commands.command(name="predict")
    async def cmd_predict(self, ctx: commands.Context, *, score: str = ""):
        if not score:
            await ctx.send("📊 Usage: !predict <your score e.g. 110-98>")
            return
        self._predictions[ctx.author.name] = score.strip()
        self._predictions_open = True
        await ctx.send(f"📊 @{ctx.author.name} predicts: {score.strip()} — let's see if they're right!")

    @commands.command(name="predictions")
    async def cmd_predictions(self, ctx: commands.Context):
        if not self._predictions:
            await ctx.send("No predictions yet! Use !predict <score> to enter.")
            return
        sample = list(self._predictions.items())[:5]
        msg = " | ".join(f"{u}: {s}" for u, s in sample)
        await ctx.send(f"📊 Predictions ({len(self._predictions)} total): {msg}")

    @commands.command(name="result")
    async def cmd_result(self, ctx: commands.Context, *, actual: str = ""):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        if not actual or not self._predictions:
            await ctx.send("Usage: !result <actual score> — announces closest predictor")
            return
        # Parse scores like "110-98"
        try:
            a_parts = [int(x) for x in actual.strip().replace(" ", "").split("-")]
            best_user, best_diff = None, 9999
            for user, pred in self._predictions.items():
                try:
                    p_parts = [int(x) for x in pred.replace(" ", "").split("-")]
                    diff = sum(abs(a - p) for a, p in zip(a_parts, p_parts))
                    if diff < best_diff:
                        best_diff, best_user = diff, user
                except Exception:
                    continue
            if best_user:
                await ctx.send(f"🏆 Closest predictor: @{best_user} with '{self._predictions[best_user]}'! (actual: {actual}) 🎉")
            self._predictions.clear()
        except Exception:
            await ctx.send(f"Actual score set to {actual}. Check predictions with !predictions")

    # ------------------------------------------------------------------ #
    #  Poll                                                                #
    # ------------------------------------------------------------------ #

    @commands.command(name="poll")
    async def cmd_poll(self, ctx: commands.Context, *, args: str = ""):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        parts = [p.strip() for p in args.split("|") if p.strip()]
        if len(parts) < 3:
            await ctx.send("Usage: !poll <question> | option1 | option2 | option3")
            return
        self._poll_question = parts[0]
        self._poll_options = parts[1:]
        self._poll_votes = {}
        self._poll_active = True
        opts = " | ".join(f"{i+1}={o}" for i, o in enumerate(self._poll_options))
        await ctx.send(f"📊 POLL: {self._poll_question} — Vote: {opts} (type the number!)")

    @commands.command(name="endpoll")
    async def cmd_endpoll(self, ctx: commands.Context):
        if not (ctx.author.is_mod or ctx.author.name.lower() == self.bot.cfg.channel.lower()):
            return
        if not self._poll_active:
            await ctx.send("No poll running.")
            return
        self._poll_active = False
        if not self._poll_votes:
            await ctx.send("Poll ended with no votes.")
            return
        counts = [0] * len(self._poll_options)
        for v in self._poll_votes.values():
            if 0 <= v < len(counts):
                counts[v] += 1
        total = sum(counts)
        results = " | ".join(
            f"{self._poll_options[i]}: {counts[i]} ({int(counts[i]/total*100)}%)"
            for i in range(len(self._poll_options))
        )
        winner_idx = counts.index(max(counts))
        await ctx.send(f"📊 Poll Results: {results} — Winner: {self._poll_options[winner_idx]}! 🏆")

    async def check_poll_vote(self, message):
        """Called from core for every message — checks if it's a poll vote."""
        if not self._poll_active or message.echo:
            return
        content = message.content.strip()
        if content.isdigit():
            idx = int(content) - 1
            if 0 <= idx < len(self._poll_options):
                self._poll_votes[message.author.name] = idx
