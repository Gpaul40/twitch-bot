"""
Discord webhook alerter — stream go-live, offline, raids, subs, clips, highlights.
"""

import logging
import httpx

logger = logging.getLogger("bot.alerts")


class DiscordAlerter:
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def _send(self, payload: dict):
        if not self.webhook_url:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.webhook_url, json=payload)
            if resp.status_code not in (200, 204):
                logger.warning(f"Discord alert failed [{resp.status_code}]")

    async def send_live_alert(self, channel: str, title: str, game: str):
        await self._send({"embeds": [{
            "title": f"🔴 {channel} is LIVE!",
            "description": f"**{title}**\nPlaying: **{game}**",
            "color": 0x9146FF,
            "url": f"https://twitch.tv/{channel}",
        }]})

    async def send_offline_alert(self, channel: str, duration: str):
        await self._send({"embeds": [{
            "title": f"⚫ {channel} is now Offline",
            "description": f"Stream lasted **{duration}**. Thanks for watching!",
            "color": 0x808080,
        }]})

    async def send_raid_alert(self, raider: str, viewers: int):
        await self._send({"embeds": [{
            "title": "⚔️ Incoming Raid!",
            "description": f"**{raider}** raided with **{viewers}** viewers!",
            "color": 0xFF6B35,
        }]})

    async def send_sub_alert(self, username: str, tier: str = "1000"):
        tier_name = {"1000": "Tier 1", "2000": "Tier 2", "3000": "Tier 3", "gift": "Gift Sub"}.get(tier, tier)
        await self._send({"embeds": [{
            "title": "🎉 New Sub!",
            "description": f"**{username}** just subscribed ({tier_name})!",
            "color": 0x00FF7F,
        }]})

    async def send_clip_alert(self, clip_url: str, triggered_by: str):
        await self._send({"embeds": [{
            "title": "✂️ New Clip Created!",
            "description": f"Triggered by **{triggered_by}**\n{clip_url}",
            "color": 0x1DA1F2,
        }]})

    async def send_highlight_candidates(self, clips: list[dict], dashboard_url: str):
        if not clips:
            return
        lines = "\n".join(
            f"{i+1}. [{c.get('title','Untitled')}]({c.get('url','')}) — {c.get('view_count',0)} views"
            for i, c in enumerate(clips)
        )
        await self._send({"embeds": [{
            "title": "🎬 Stream Over — Highlight Candidates",
            "description": f"{lines}\n\n[→ Promote to Highlights]({dashboard_url})",
            "color": 0xFFD700,
        }]})

