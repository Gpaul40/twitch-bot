"""
Channel point reward handler.
"""

import logging

logger = logging.getLogger("bot.rewards")


class RewardHandler:
    def __init__(self, bot):
        self.bot = bot

    async def handle(self, event):
        reward_title = event.reward.title.lower()
        username = event.user.name
        logger.info(f"Reward redeemed: '{reward_title}' by {username}")
        await self.bot.stats.record_event("reward", username=username, extra=reward_title)

        if "clip" in reward_title:
            clip = await self.bot.clipper.create_clip(
                self.bot.cfg.broadcaster_id,
                title=f"Reward clip by {username}",
            )
            if clip:
                self.bot.highlight_mgr.record_clip(clip)
                channel = self.bot.get_channel(self.bot.cfg.channel)
                if channel:
                    await channel.send(f"✂️ Clipped for @{username}! {clip['edit_url']}")

        # Add custom reward handlers here:
        # elif "hydrate" in reward_title:
        #     channel = self.bot.get_channel(self.bot.cfg.channel)
        #     await channel.send(f"💧 {username} says: drink water!")

