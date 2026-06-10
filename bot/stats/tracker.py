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
                CREATE TABLE IF NOT EXISTS custom_commands (
                    name TEXT PRIMARY KEY,
                    response TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS death_counter (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    count INTEGER DEFAULT 0
                );
                INSERT OR IGNORE INTO death_counter (id, count) VALUES (1, 0);
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

    # ------------------------------------------------------------------ #
    #  Custom commands                                                     #
    # ------------------------------------------------------------------ #

    async def set_custom_command(self, name: str, response: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO custom_commands (name, response) VALUES (?, ?)",
                (name, response),
            )
            await db.commit()

    async def delete_custom_command(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM custom_commands WHERE name = ?", (name,))
            await db.commit()

    async def get_custom_command(self, name: str) -> str | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT response FROM custom_commands WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_custom_commands(self) -> list[str]:
        """Return a list of all custom command names."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT name FROM custom_commands ORDER BY name")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    # ------------------------------------------------------------------ #
    #  Death counter                                                       #
    # ------------------------------------------------------------------ #

    async def increment_deaths(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE death_counter SET count = count + 1 WHERE id = 1")
            await db.commit()
            cursor = await db.execute("SELECT count FROM death_counter WHERE id = 1")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_deaths(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT count FROM death_counter WHERE id = 1")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def reset_deaths(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE death_counter SET count = 0 WHERE id = 1")
            await db.commit()
