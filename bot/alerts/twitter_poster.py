"""
Twitter/X auto-poster.

Posts automatically when:
  - Stream goes LIVE (go-live tweet with stream link)
  - A clip is created (tweet the clip URL)
  - Stream ends (end-of-stream recap tweet)

Requires a Twitter Developer App with OAuth 1.0a credentials.
Get them at: https://developer.twitter.com/en/portal/dashboard
Free tier supports posting tweets.
"""

import logging
import asyncio

logger = logging.getLogger("bot.twitter")


class TwitterPoster:
    def __init__(self, cfg):
        self.cfg = cfg
        self._client = None

        if not all([cfg.twitter_api_key, cfg.twitter_api_secret,
                    cfg.twitter_access_token, cfg.twitter_access_secret]):
            logger.warning("Twitter credentials not set — auto-posting disabled.")
            return

        try:
            import tweepy
            auth = tweepy.OAuth1UserHandler(
                cfg.twitter_api_key,
                cfg.twitter_api_secret,
                cfg.twitter_access_token,
                cfg.twitter_access_secret,
            )
            self._client = tweepy.API(auth, wait_on_rate_limit=True)
            logger.info("✅ Twitter/X auto-poster enabled.")
        except ImportError:
            logger.warning("tweepy not installed — run: pip install tweepy")
        except Exception as e:
            logger.error(f"Twitter init error: {e}")

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def _post(self, text: str):
        if not self._client:
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._client.update_status, text)
            logger.info(f"Tweet posted: {text[:60]}...")
        except Exception as e:
            logger.error(f"Tweet failed: {e}")

    async def post_go_live(self, channel: str, title: str, game: str):
        text = (
            f"🔴 LIVE NOW on Twitch!\n\n"
            f"🎮 {title}\n"
            f"Playing: {game}\n\n"
            f"🔗 https://twitch.tv/{channel}\n\n"
            f"#Twitch #TwitchStreamer #{game.replace(' ', '')} #Live"
        )
        await self._post(text[:280])

    async def post_clip(self, clip_url: str, title: str, channel: str):
        text = (
            f"✂️ New clip just dropped!\n\n"
            f"🎬 {title}\n"
            f"🔗 {clip_url}\n\n"
            f"Follow for more 👉 https://twitch.tv/{channel}\n"
            f"#Twitch #Clip #Gaming"
        )
        await self._post(text[:280])

    async def post_go_offline(self, channel: str, duration: str, clip_count: int):
        text = (
            f"Stream wrapped! {duration} of content 🎮\n\n"
            f"Made {clip_count} clip{'s' if clip_count != 1 else ''} tonight — highlights dropping soon.\n"
            f"Follow on Twitch so you don't miss the next one 🔔\n"
            f"👉 https://twitch.tv/{channel}"
        )
        await self._post(text[:280])
