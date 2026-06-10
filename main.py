"""
Twitch Bot — Entry point
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from bot.core import TwitchBot


def main():
    token = os.getenv("TWITCH_OAUTH_TOKEN", "").replace("oauth:", "")
    bot = TwitchBot(
        token=token,
        client_id=os.getenv("TWITCH_CLIENT_ID", ""),
        client_secret=os.getenv("TWITCH_CLIENT_SECRET", ""),
        channel=os.getenv("TWITCH_CHANNEL", ""),
    )
    bot.run()


if __name__ == "__main__":
    main()
