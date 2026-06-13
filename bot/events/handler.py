"""
Rich event handler — subs, resubs, gift subs, cheers, follows, bits.
Responds in chat and fires Discord alerts.
"""

import logging
from bot.clipping.clipper import Clipper

logger = logging.getLogger("bot.events")

# Cheer milestone thresholds
CHEER_MILESTONES = [100, 500, 1000, 5000, 10000]


class EventHandler:
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------ #
    #  Subscriptions                                                       #
    # ------------------------------------------------------------------ #

    async def on_sub(self, event):
        username = event.user.name
        tier = getattr(event, "sub_plan", "1000")
        tier_name = {"1000": "Tier 1 👑", "2000": "Tier 2 💎", "3000": "Tier 3 🔥"}.get(tier, "Tier 1")
        logger.info(f"New sub: {username} ({tier_name})")

        await self._chat(f"🎉 Welcome to the fam, @{username}! Thanks for the {tier_name} sub! 🙌")
        await self.bot.stats.record_event("sub", username=username, extra=tier)
        await self.bot.alerter.send_sub_alert(username, tier)

        # Auto-clip on sub if stream is live
        if self.bot.stream_monitor.is_live:
            clip = await self.bot.clipper.create_clip(
                self.bot.cfg.broadcaster_id, title=f"Sub moment — {username}"
            )
            if clip:
                self.bot.highlight_mgr.record_clip(clip)

    async def on_resub(self, event):
        username = event.user.name
        months = getattr(event, "cumulative_months", 1)
        msg = getattr(event, "message", {})
        sub_msg = msg.get("message", "") if isinstance(msg, dict) else ""
        logger.info(f"Resub: {username} x{months} months")

        chat_msg = f"♻️ @{username} just resubbed for {months} months! "
        if sub_msg:
            chat_msg += f'"{sub_msg}" '
        chat_msg += "Thank you! ❤️"
        await self._chat(chat_msg)
        await self.bot.stats.record_event("resub", username=username, extra=str(months))

    async def on_giftsub(self, event):
        gifter = getattr(event.user, "name", "Anonymous")
        recipient = getattr(event, "recipient", {})
        recipient_name = recipient.get("display_name", "someone") if isinstance(recipient, dict) else str(recipient)
        logger.info(f"Gift sub: {gifter} → {recipient_name}")

        await self._chat(f"🎁 @{gifter} just gifted a sub to @{recipient_name}! What a legend! 👏")
        await self.bot.stats.record_event("giftsub", username=gifter, extra=recipient_name)
        await self.bot.alerter.send_sub_alert(f"{gifter} → {recipient_name}", "gift")

    # ------------------------------------------------------------------ #
    #  Bits / Cheers                                                       #
    # ------------------------------------------------------------------ #

    async def on_cheer(self, event):
        username = event.user.name
        bits = event.bits_used
        total = event.total_bits_used
        logger.info(f"Cheer: {username} — {bits} bits (total: {total})")

        await self._chat(f"💜 @{username} cheered {bits} bits! Total: {total} bits! Thank you so much!")
        await self.bot.stats.record_event("cheer", username=username, extra=str(bits))

        # Milestone clips
        for milestone in CHEER_MILESTONES:
            if bits >= milestone:
                if self.bot.stream_monitor.is_live:
                    clip = await self.bot.clipper.create_clip(
                        self.bot.cfg.broadcaster_id,
                        title=f"{bits} bit cheer by {username}",
                    )
                    if clip:
                        url = Clipper.public_url(clip)
                        self.bot.highlight_mgr.record_clip(clip)
                        await self.bot.alerter.send_clip_alert(url, triggered_by=f"{username} ({bits} bits)")
                break

    # ------------------------------------------------------------------ #
    #  Follows                                                             #
    # ------------------------------------------------------------------ #

    async def on_follow(self, event):
        username = event.user.name
        logger.info(f"New follow: {username}")
        await self._chat(f"💙 @{username} just followed! Welcome to the channel! 🎮")
        await self.bot.stats.record_event("follow", username=username)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    async def _chat(self, msg: str):
        channel = self.bot.get_channel(self.bot.cfg.channel)
        if channel:
            await channel.send(msg)
