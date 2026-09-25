import discord
from datetime import datetime, timezone

import config


async def send_log(guild: discord.Guild, title: str, description: str,
                    color: discord.Color = discord.Color.orange(),
                    fields: list[tuple[str, str]] | None = None):
    """Posts a standardized embed to the guild's mod-log channel, if it exists."""
    channel = discord.utils.get(guild.text_channels, name=config.MOD_LOG_CHANNEL_NAME)
    if channel is None:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass
