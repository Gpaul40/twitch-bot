"""
Core bot class — wires together all modules.
"""

import logging
from twitchio.ext import commands

from bot.config import cfg
from bot.helix import HelixClient
from bot.clipping.clipper import Clipper
from bot.clipping.highlight import HighlightManager
from bot.stats.tracker import StatsTracker
from bot.alerts.discord import DiscordAlerter
from bot.rewards.handler import RewardHandler
from bot.events.handler import EventHandler
from bot.stream_monitor import StreamMonitor
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
    def __init__(self):
        super().__init__(
            token=cfg.oauth_token,
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            prefix="!",
            initial_channels=[cfg.channel],
        )
        self.cfg = cfg

        # Shared services
        self.helix = HelixClient(
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            oauth_token=cfg.oauth_token,
            refresh_token=cfg.refresh_token,
        )
        self.stats = StatsTracker(db_path=cfg.stats_db)
        self.alerter = DiscordAlerter(webhook_url=cfg.discord_webhook)
        self.clipper = Clipper(helix=self.helix, cfg=cfg)
        self.highlight_mgr = HighlightManager(helix=self.helix, alerter=self.alerter, stats=self.stats)
        self.stream_monitor = StreamMonitor(
            helix=self.helix,
            stats=self.stats,
            alerter=self.alerter,
            clipper=self.clipper,
            cfg=cfg,
        )
        self.event_handler = EventHandler(bot=self)
        self.reward_handler = RewardHandler(bot=self)

        # Register command cogs
        self.add_cog(general.GeneralCommands(self))
        self.add_cog(clips.ClipCommands(self))
        self.add_cog(stats_cmds.StatsCommands(self))

    async def event_ready(self):
        logger.info(f"✅ Bot online as {self.nick} | Watching: #{self.cfg.channel}")
        await self.stats.init_db()
        self.stream_monitor.start()

    async def event_message(self, message):
        if message.echo:
            return
        await self.stats.record_message(message)
        clip = await self.clipper.check_auto_clip_trigger(message, self.cfg.broadcaster_id)
        if clip:
            self.highlight_mgr.record_clip(clip)
            await self.alerter.send_clip_alert(clip["edit_url"], triggered_by=message.author.name)
        await self.handle_commands(message)

    async def event_raid(self, raid):
        logger.info(f"Raid from {raid.raider.name} with {raid.viewer_count} viewers!")
        await self.alerter.send_raid_alert(raid.raider.name, raid.viewer_count)
        await self.stats.record_event("raid", username=raid.raider.name, extra=str(raid.viewer_count))
        if self.cfg.auto_clip_on_raid:
            clip = await self.clipper.create_clip(
                self.cfg.broadcaster_id, title=f"Raid from {raid.raider.name}"
            )
            if clip:
                self.highlight_mgr.record_clip(clip)

    # Delegate sub/cheer/follow events to EventHandler
    async def event_usernotice_subscription(self, event):
        await self.event_handler.on_sub(event)

    async def event_usernotice_resubscription(self, event):
        await self.event_handler.on_resub(event)

    async def event_usernotice_giftsub(self, event):
        await self.event_handler.on_giftsub(event)

    async def event_channel_points_redeemed(self, event):
        await self.reward_handler.handle(event)

