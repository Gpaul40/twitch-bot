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
from bot.scheduled import ScheduledMessages
from bot.commands import general, clips, stats as stats_cmds
from bot.commands.fun import FunCommands
from bot.commands.mod_cmds import ModCommands
from bot.commands.ai_cmd import AICommands
from bot.queue import QueueCommands

import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
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
        self.clipper = Clipper(helix=self.helix, cfg=cfg, stats=self.stats)
        self.highlight_mgr = HighlightManager(helix=self.helix, alerter=self.alerter, stats=self.stats)
        self.stream_monitor = StreamMonitor(
            helix=self.helix,
            stats=self.stats,
            alerter=self.alerter,
            clipper=self.clipper,
            highlight_mgr=self.highlight_mgr,
            cfg=cfg,
        )
        self.event_handler = EventHandler(bot=self)
        self.reward_handler = RewardHandler(bot=self)
        self.scheduled = ScheduledMessages(bot=self, interval_seconds=cfg.scheduled_msg_interval)

        # Track first-time chatters per session (reset on bot restart)
        self._seen_chatters: set[str] = set()

        # Register command cogs
        self.add_cog(general.GeneralCommands(self))
        self.add_cog(clips.ClipCommands(self))
        self.add_cog(stats_cmds.StatsCommands(self))
        self.add_cog(FunCommands(self))
        self.add_cog(ModCommands(self))
        self.add_cog(AICommands(self))
        self._queue_cog = QueueCommands(self)
        self.add_cog(self._queue_cog)

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    async def event_ready(self):
        logger.info(f"✅ Bot online as {self.nick} | Watching: #{self.cfg.channel}")
        await self.stats.init_db()
        self.stream_monitor.start()
        self.scheduled.start()

    # ------------------------------------------------------------------ #
    #  Messages                                                            #
    # ------------------------------------------------------------------ #

    async def event_message(self, message):
        if message.echo:
            return

        await self.stats.record_message(message)

        # Welcome first-time chatters
        if self.cfg.welcome_new_chatters and message.author.name not in self._seen_chatters:
            self._seen_chatters.add(message.author.name)
            if self.stream_monitor.is_live:
                await message.channel.send(
                    f"👋 Welcome to the stream, @{message.author.name}! 🎮 Use !commands to see what I can do!"
                )

        # Auto-clip on keyword trigger (only when live)
        clip = await self.clipper.check_auto_clip_trigger(
            message, self.cfg.broadcaster_id, is_live=self.stream_monitor.is_live
        )
        if clip:
            self.highlight_mgr.record_clip(clip)
            await self.alerter.send_clip_alert(clip["edit_url"], triggered_by=message.author.name)

        # Check custom commands BEFORE built-in command routing
        content = message.content.strip()
        if content.startswith("!"):
            cmd_name = content[1:].split()[0].lower()
            custom_response = await self.stats.get_custom_command(cmd_name)
            if custom_response:
                await message.channel.send(custom_response)
                return  # Don't fall through to built-in commands

        await self.handle_commands(message)

    # ------------------------------------------------------------------ #
    #  Raids                                                               #
    # ------------------------------------------------------------------ #

    async def event_raid(self, raid):
        logger.info(f"Raid from {raid.raider.name} with {raid.viewer_count} viewers!")
        await self.alerter.send_raid_alert(raid.raider.name, raid.viewer_count)
        await self.stats.record_event("raid", username=raid.raider.name, extra=str(raid.viewer_count))

        channel = self.get_channel(self.cfg.channel)
        if channel:
            await channel.send(
                f"🔥 Welcome raiders from @{raid.raider.name} and their {raid.viewer_count} viewers! "
                f"Give them a follow at https://twitch.tv/{raid.raider.name} ❤️"
            )

        if self.cfg.auto_clip_on_raid:
            clip = await self.clipper.create_clip(
                self.cfg.broadcaster_id, title=f"Raid from {raid.raider.name}"
            )
            if clip:
                self.highlight_mgr.record_clip(clip)

    # ------------------------------------------------------------------ #
    #  Sub / cheer / follow events — delegated to EventHandler            #
    # ------------------------------------------------------------------ #

    async def event_usernotice_subscription(self, event):
        await self.event_handler.on_sub(event)

    async def event_usernotice_resubscription(self, event):
        await self.event_handler.on_resub(event)

    async def event_usernotice_giftsub(self, event):
        await self.event_handler.on_giftsub(event)

    async def event_usernotice_mysterygiftsub(self, event):
        gifter = getattr(event.user, "name", "Anonymous")
        gift_count = getattr(event, "gift_count", 1)
        logger.info(f"Mass gift sub: {gifter} gifted {gift_count} subs!")
        channel = self.get_channel(self.cfg.channel)
        if channel:
            await channel.send(
                f"🎁 @{gifter} just gifted {gift_count} subs to the community! What an absolute legend! 🔥"
            )
        await self.stats.record_event("mass_giftsub", username=gifter, extra=str(gift_count))

    async def event_cheer(self, event):
        await self.event_handler.on_cheer(event)

    async def event_follow(self, event):
        await self.event_handler.on_follow(event)

    async def event_channel_points_redeemed(self, event):
        await self.reward_handler.handle(event)

    # ------------------------------------------------------------------ #
    #  Expose cogs for dashboard access                                    #
    # ------------------------------------------------------------------ #

    @property
    def fun_cog(self) -> FunCommands:
        return self.cogs.get("FunCommands")

    @property
    def queue_cog(self) -> QueueCommands:
        return self._queue_cog

