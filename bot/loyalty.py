"""
Viewer loyalty points system.

Points are earned by:
  - Watching (1 point per minute while stream is live — polled every 5 min)
  - Chatting (1 point per message)
  - Subscribing (100 points)
  - Gifting subs (50 points per gift)
  - Cheering bits (1 point per 10 bits)

Commands:
  !points        — check your point balance
  !toppoints     — top 10 point holders
  !redeem <item> — redeem a reward (broadcaster sets up via !addreward)
"""

import asyncio
import logging
import aiosqlite

logger = logging.getLogger("bot.points")

POINTS_PER_MESSAGE = 1
POINTS_PER_WATCH_INTERVAL = 2    # awarded every 5 min to active chatters
POINTS_PER_SUB = 100
POINTS_PER_GIFTSUB = 50
POINTS_PER_10_BITS = 1
WATCH_INTERVAL = 300              # 5 minutes


class LoyaltyPoints:
    def __init__(self, db_path: str, bot):
        self.db_path = db_path
        self.bot = bot
        self._task: asyncio.Task | None = None

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS points (
                    username TEXT PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS rewards (
                    name TEXT PRIMARY KEY,
                    cost INTEGER NOT NULL,
                    description TEXT DEFAULT ''
                );
            """)
            await db.commit()

    def start(self):
        self._task = asyncio.create_task(self._watch_loop(), name="loyalty-watch")
        logger.info("Loyalty points system started.")

    async def _watch_loop(self):
        """Award watch-time points to recent chatters every 5 minutes."""
        while True:
            try:
                await asyncio.sleep(WATCH_INTERVAL)
                if self.bot.stream_monitor.is_live:
                    await self._award_watch_points()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Loyalty watch loop error: {e}")

    async def _award_watch_points(self):
        """Award points to everyone who chatted in the last 5 minutes."""
        recent = set(self.bot._seen_chatters)
        if not recent:
            return
        async with aiosqlite.connect(self.db_path) as db:
            for username in recent:
                await db.execute(
                    "INSERT INTO points (username, balance, total_earned) VALUES (?, ?, ?) "
                    "ON CONFLICT(username) DO UPDATE SET balance=balance+?, total_earned=total_earned+?",
                    (username, POINTS_PER_WATCH_INTERVAL, POINTS_PER_WATCH_INTERVAL,
                     POINTS_PER_WATCH_INTERVAL, POINTS_PER_WATCH_INTERVAL)
                )
            await db.commit()

    async def add_points(self, username: str, amount: int, reason: str = ""):
        if amount <= 0:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO points (username, balance, total_earned) VALUES (?, ?, ?) "
                "ON CONFLICT(username) DO UPDATE SET balance=balance+?, total_earned=total_earned+?",
                (username, amount, amount, amount, amount)
            )
            await db.commit()
        if reason:
            logger.debug(f"Points +{amount} to {username} ({reason})")

    async def get_points(self, username: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT balance FROM points WHERE username=?", (username,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def deduct_points(self, username: str, amount: int) -> bool:
        bal = await self.get_points(username)
        if bal < amount:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE points SET balance=balance-? WHERE username=?", (amount, username))
            await db.commit()
        return True

    async def get_top(self, limit: int = 10) -> list[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT username, balance FROM points ORDER BY balance DESC LIMIT ?", (limit,)
            )
            return await cursor.fetchall()

    async def add_reward(self, name: str, cost: int, description: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO rewards (name, cost, description) VALUES (?,?,?)",
                (name, cost, description)
            )
            await db.commit()

    async def get_rewards(self) -> list[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT name, cost, description FROM rewards ORDER BY cost")
            return await cursor.fetchall()

    async def get_reward(self, name: str) -> tuple | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT name, cost, description FROM rewards WHERE name=?", (name.lower(),))
            return await cursor.fetchone()
