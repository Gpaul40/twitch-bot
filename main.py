"""
Twitch Bot — Entry point.

Runs the bot and the web dashboard concurrently.
"""

import asyncio
import logging
import os
import signal

import uvicorn

# Create dirs before any module imports that set up file logging
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

from bot.config import cfg  # validates env vars immediately
from bot.core import TwitchBot
from dashboard.app import app as dashboard_app, set_bot

logger = logging.getLogger("main")


async def run_dashboard(bot: TwitchBot):
    set_bot(bot)
    config = uvicorn.Config(
        dashboard_app,
        host=cfg.dashboard_host,
        port=cfg.dashboard_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    bot = TwitchBot()

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _shutdown(*_):
        logger.info("Shutdown signal received.")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler for all signals

    dashboard_task = asyncio.create_task(run_dashboard(bot), name="dashboard")
    bot_task = asyncio.create_task(bot.start(), name="twitch-bot")

    logger.info(f"Dashboard: http://{cfg.dashboard_host}:{cfg.dashboard_port}")
    logger.info(f"Joining channel: #{cfg.channel}")

    try:
        done, pending = await asyncio.wait(
            [dashboard_task, bot_task],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in done:
            if task.exception():
                logger.error(f"Task {task.get_name()} failed: {task.exception()}")
    finally:
        for task in [dashboard_task, bot_task]:
            if not task.done():
                task.cancel()
        await asyncio.gather(dashboard_task, bot_task, return_exceptions=True)
        logger.info("Bot shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(main())

