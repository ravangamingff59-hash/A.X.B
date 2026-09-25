import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True   # needed for automod text scanning
intents.members = True           # needed for kick/ban/mute member lookups and join events


class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=PREFIX, intents=intents, help_command=None)

    async def setup_hook(self):
        # Load every cog in ./cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                extension = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    log.info(f"Loaded extension: {extension}")
                except Exception as e:
                    log.exception(f"Failed to load extension {extension}: {e}")

        # Sync slash commands globally (can take up to an hour to propagate;
        # for instant testing, sync to a single guild instead — see README)
        try:
            synced = await self.tree.sync()
            log.info(f"Synced {len(synced)} slash command(s).")
        except Exception as e:
            log.exception(f"Slash command sync failed: {e}")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="the server 👀"
            )
        )


async def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Create a .env file (see .env.example)."
        )
    bot = ModBot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
