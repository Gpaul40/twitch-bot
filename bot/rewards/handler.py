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

        if "clip" in reward_title:
            await self.bot.clipper.create_clip(
                self.bot.broadcaster_id,
                title=f"Reward clip by {username}",
            )

        # Add custom reward handlers here
        # elif "hydrate" in reward_title:
        #     await event.channel.send(f"@{username} reminded the streamer to drink water! 💧")
