"""
Auto-raid engine.

When your stream ends, automatically raids another streamer to:
  - Keep your community together
  - Build relationships with other streamers (they often raid back)
  - Grow your network

Priority order:
  1. RAID_TARGETS list in .env (your friends/regulars)
  2. A random small streamer playing the same game (organic discovery)

Uses Twitch Helix API to trigger the raid.
"""

import logging
import random
import httpx

logger = logging.getLogger("bot.autoraid")

BASE = "https://api.twitch.tv/helix"


class AutoRaider:
    def __init__(self, helix, cfg):
        self.helix = helix
        self.cfg = cfg

    async def raid_out(self, current_game_name: str = "") -> bool:
        """
        Called when stream ends. Finds a target and raids them.
        Returns True if raid was sent.
        """
        if not self.cfg.auto_raid_out:
            return False

        target = await self._find_target(current_game_name)
        if not target:
            logger.info("Auto-raid: no suitable target found.")
            return False

        success = await self._send_raid(target["id"], target["display_name"])
        return success

    async def _find_target(self, game_name: str) -> dict | None:
        # 1. Try configured targets first
        targets = self.cfg.raid_targets
        if targets:
            random.shuffle(targets)
            for login in targets:
                user = await self.helix.get_user(login=login)
                if user:
                    # Check they're live
                    stream = await self.helix.get_stream(user["id"])
                    if stream:
                        logger.info(f"Auto-raid target (configured): {login}")
                        return {"id": user["id"], "display_name": user["display_name"]}

        # 2. Find a small streamer in the same game
        if game_name:
            game = await self.helix.get_game_by_name(game_name)
            if game:
                streams = await self._get_streams_by_game(game["id"], first=20)
                # Filter: 5-50 viewers (organic, not mega-streamers)
                candidates = [s for s in streams
                              if 5 <= s.get("viewer_count", 0) <= 50
                              and s["user_id"] != self.cfg.broadcaster_id]
                if candidates:
                    target = random.choice(candidates)
                    logger.info(f"Auto-raid target (discovery): {target['user_name']} ({target['viewer_count']} viewers)")
                    return {"id": target["user_id"], "display_name": target["user_name"]}

        return None

    async def _get_streams_by_game(self, game_id: str, first: int = 20) -> list[dict]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{BASE}/streams",
                    headers=await self.helix._headers(),
                    params={"game_id": game_id, "first": str(first)},
                )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"get_streams_by_game error: {e}")
        return []

    async def _send_raid(self, target_id: str, target_name: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{BASE}/raids",
                    headers=await self.helix._headers(),
                    params={
                        "from_broadcaster_id": self.cfg.broadcaster_id,
                        "to_broadcaster_id": target_id,
                    },
                )
            if resp.status_code in (200, 204):
                logger.info(f"✅ Raiding {target_name}!")
                return True
            else:
                logger.error(f"Raid failed [{resp.status_code}]: {resp.text}")
        except Exception as e:
            logger.error(f"Raid error: {e}")
        return False
