"""
Core bot class — wires together all modules.
"""

import os
import logging
from twitchio.ext import commands

from bot.clipping.clipper import Clipper
from bot.stats.tracker import StatsTracker
from bot.alerts.discord import DiscordAlerter
from bot.rewards.handler import RewardHandler
from bot.commands import general, clips, stats as stats_cmds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log"),
    ],
)
logger = logging.getLogger("bot.core")


class TwitchBot(commands.Bot):
    def __init__(self, token: str, client_id: str, client_secret: str, channel: str):
        super().__init__(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            prefix="!",
            initial_channels=[channel],
        )
        self.channel_name = channel
        self.broadcaster_id = os.getenv("TWITCH_BROADCASTER_ID", "")

        self.clipper = Clipper(client_id=client_id, oauth_token=token)
        self.stats = StatsTracker(db_path=os.getenv("STATS_DB_PATH", "data/stats.db"))
        self.alerter = DiscordAlerter(webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""))
        self.reward_handler = RewardHandler(self)

        # Register command cogs
        self.add_cog(general.GeneralCommands(self))
        self.add_cog(clips.ClipCommands(self))
        self.add_cog(stats_cmds.StatsCommands(self))

    async def event_ready(self):
        logger.info(f"Bot online | {self.nick}")
        await self.stats.init_db()

    async def event_message(self, message):
        if message.echo:
            return

        await self.stats.record_message(message)
        await self.clipper.check_auto_clip_trigger(message, self.broadcaster_id)
        await self.handle_commands(message)

    async def event_raid(self, raid):
        logger.info(f"Raid from {raid.raider.name} with {raid.viewer_count} viewers!")
        if os.getenv("AUTO_CLIP_ON_RAID", "true").lower() == "true":
            await self.clipper.create_clip(self.broadcaster_id, title=f"Raid from {raid.raider.name}")
        await self.alerter.send_raid_alert(raid.raider.name, raid.viewer_count)

    async def event_channel_points_redeemed(self, event):
        await self.reward_handler.handle(event)
