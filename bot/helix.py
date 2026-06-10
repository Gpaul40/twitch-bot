"""
Twitch Helix API client with automatic OAuth token refresh.

Covers:
  - Clips (create, list, get)
  - Streams (get live status)
  - Users (get by login/id)
  - Channel info (game, title)
  - Highlights / Videos
  - Hype Train events
"""

import logging
import time
import asyncio
import httpx
from typing import Optional

logger = logging.getLogger("bot.helix")

BASE = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"


class HelixClient:
    def __init__(self, client_id: str, client_secret: str, oauth_token: str, refresh_token: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_token = oauth_token
        self.refresh_token = refresh_token
        self._token_expiry: float = 0.0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    #  Token management                                                    #
    # ------------------------------------------------------------------ #

    async def _ensure_token(self):
        """Refresh the access token if it's expired or about to expire."""
        if time.time() < self._token_expiry - 60:
            return
        async with self._lock:
            if time.time() >= self._token_expiry - 60:
                await self._refresh()

    async def _refresh(self):
        if not self.refresh_token:
            logger.warning("No refresh token — cannot auto-refresh OAuth token.")
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
        if resp.status_code == 200:
            data = resp.json()
            self.oauth_token = data["access_token"]
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            self._token_expiry = time.time() + data.get("expires_in", 14400)
            logger.info("OAuth token refreshed successfully.")
        else:
            logger.error(f"Token refresh failed [{resp.status_code}]: {resp.text}")

    async def _headers(self) -> dict:
        await self._ensure_token()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.oauth_token}",
        }

    async def _get(self, path: str, params: dict = None) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE}{path}", headers=await self._headers(), params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"GET {path} [{resp.status_code}]: {resp.text}")
        return None

    async def _post(self, path: str, params: dict = None, json: dict = None) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BASE}{path}",
                headers=await self._headers(),
                params=params,
                json=json,
            )
        if resp.status_code in (200, 202):
            return resp.json()
        logger.error(f"POST {path} [{resp.status_code}]: {resp.text}")
        return None

    # ------------------------------------------------------------------ #
    #  Clips                                                               #
    # ------------------------------------------------------------------ #

    async def create_clip(self, broadcaster_id: str) -> Optional[dict]:
        """Create a clip. Returns {'id': ..., 'edit_url': ...} or None."""
        data = await self._post("/clips", params={"broadcaster_id": broadcaster_id})
        if data and data.get("data"):
            return data["data"][0]
        return None

    async def get_clips(self, broadcaster_id: str, first: int = 10) -> list[dict]:
        """Get most recent clips for a broadcaster."""
        data = await self._get("/clips", params={"broadcaster_id": broadcaster_id, "first": str(first)})
        return data.get("data", []) if data else []

    async def get_clip(self, clip_id: str) -> Optional[dict]:
        data = await self._get("/clips", params={"id": clip_id})
        if data and data.get("data"):
            return data["data"][0]
        return None

    # ------------------------------------------------------------------ #
    #  Streams                                                             #
    # ------------------------------------------------------------------ #

    async def get_stream(self, broadcaster_id: str) -> Optional[dict]:
        """Returns stream object if live, None if offline."""
        data = await self._get("/streams", params={"user_id": broadcaster_id})
        if data and data.get("data"):
            return data["data"][0]
        return None

    async def is_live(self, broadcaster_id: str) -> bool:
        return await self.get_stream(broadcaster_id) is not None

    # ------------------------------------------------------------------ #
    #  Channel / Users                                                     #
    # ------------------------------------------------------------------ #

    async def get_channel_info(self, broadcaster_id: str) -> Optional[dict]:
        data = await self._get("/channels", params={"broadcaster_id": broadcaster_id})
        if data and data.get("data"):
            return data["data"][0]
        return None

    async def get_user(self, login: str = None, user_id: str = None) -> Optional[dict]:
        params = {}
        if login:
            params["login"] = login
        if user_id:
            params["id"] = user_id
        data = await self._get("/users", params=params)
        if data and data.get("data"):
            return data["data"][0]
        return None

    # ------------------------------------------------------------------ #
    #  Videos / Highlights                                                 #
    # ------------------------------------------------------------------ #

    async def get_videos(self, broadcaster_id: str, video_type: str = "highlight", first: int = 10) -> list[dict]:
        """Get VODs or highlights. video_type: 'archive' | 'highlight' | 'upload'"""
        data = await self._get("/videos", params={
            "user_id": broadcaster_id,
            "type": video_type,
            "first": str(first),
        })
        return data.get("data", []) if data else []

    async def create_highlight_from_clip(self, clip: dict) -> str:
        """
        Twitch doesn't have a direct 'create highlight from clip' API endpoint.
        This returns the clip URL as a highlight candidate with instructions.
        Real highlight creation requires the Twitch dashboard or video editor.
        """
        return clip.get("url", "")

    # ------------------------------------------------------------------ #
    #  Hype Train                                                          #
    # ------------------------------------------------------------------ #

    async def get_hype_train(self, broadcaster_id: str) -> Optional[dict]:
        data = await self._get("/hypetrain/events", params={"broadcaster_id": broadcaster_id})
        if data and data.get("data"):
            return data["data"][0]
        return None

    # ------------------------------------------------------------------ #
    #  Channel management                                                  #
    # ------------------------------------------------------------------ #

    async def update_channel(
        self,
        broadcaster_id: str,
        title: str = None,
        game_id: str = None,
    ) -> bool:
        """PATCH /channels — update title and/or game. Requires channel:manage:broadcast scope."""
        payload = {}
        if title is not None:
            payload["title"] = title
        if game_id is not None:
            payload["game_id"] = game_id
        if not payload:
            return False
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{BASE}/channels",
                headers=await self._headers(),
                params={"broadcaster_id": broadcaster_id},
                json=payload,
            )
        if resp.status_code == 204:
            return True
        logger.error(f"PATCH /channels [{resp.status_code}]: {resp.text}")
        return False

    async def get_game_by_name(self, name: str) -> Optional[dict]:
        """Look up a game by name. Returns the first match or None."""
        data = await self._get("/games", params={"name": name})
        if data and data.get("data"):
            return data["data"][0]
        return None
