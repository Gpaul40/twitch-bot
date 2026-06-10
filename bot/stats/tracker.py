"""
Stats tracker — records messages, commands, follows, subs to SQLite.
"""

import logging
import aiosqlite

logger = logging.getLogger("bot.stats")


class StatsTracker:
    def __init__(self, db_path: str = "data/stats.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    username TEXT,
                    extra TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS clips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_id TEXT,
                    edit_url TEXT,
                    triggered_by TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
        logger.info("Stats DB initialised.")

    async def record_message(self, message):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (username, channel, content) VALUES (?, ?, ?)",
                (message.author.name, message.channel.name, message.content),
            )
            await db.commit()

    async def record_event(self, event_type: str, username: str = "", extra: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO events (event_type, username, extra) VALUES (?, ?, ?)",
                (event_type, username, extra),
            )
            await db.commit()

    async def get_top_chatters(self, limit: int = 5) -> list[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT username, COUNT(*) as cnt FROM messages GROUP BY username ORDER BY cnt DESC LIMIT ?",
                (limit,),
            )
            return await cursor.fetchall()

    async def get_message_count(self, username: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE username = ?", (username,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
