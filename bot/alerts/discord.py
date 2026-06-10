"""
Discord webhook alerter — stream go-live, raids, subs, follows.
"""

import logging
import aiohttp

logger = logging.getLogger("bot.alerts")


class DiscordAlerter:
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def _send(self, payload: dict):
        if not self.webhook_url:
            return
        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=payload) as resp:
                if resp.status not in (200, 204):
                    logger.warning(f"Discord alert failed [{resp.status}]")

    async def send_live_alert(self, channel: str, title: str, game: str):
        await self._send({
            "embeds": [{
                "title": f"🔴 {channel} is LIVE!",
                "description": f"**{title}**\nPlaying: {game}",
                "color": 0x9146FF,
                "url": f"https://twitch.tv/{channel}",
            }]
        })

    async def send_raid_alert(self, raider: str, viewers: int):
        await self._send({
            "embeds": [{
                "title": "⚔️ Incoming Raid!",
                "description": f"**{raider}** raided with **{viewers}** viewers!",
                "color": 0xFF6B35,
            }]
        })

    async def send_sub_alert(self, username: str, tier: str = "1000"):
        tier_name = {"1000": "Tier 1", "2000": "Tier 2", "3000": "Tier 3"}.get(tier, tier)
        await self._send({
            "embeds": [{
                "title": "🎉 New Sub!",
                "description": f"**{username}** just subscribed ({tier_name})!",
                "color": 0x00FF7F,
            }]
        })

    async def send_clip_alert(self, clip_url: str, triggered_by: str):
        await self._send({
            "embeds": [{
                "title": "✂️ New Clip Created!",
                "description": f"Triggered by **{triggered_by}**\n{clip_url}",
                "color": 0x1DA1F2,
            }]
        })
