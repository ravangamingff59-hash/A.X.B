"""
Central configuration for the moderation bot.
Adjust these values (or wire them up to a per-guild settings DB later).
"""

# --- Logging ---
# Channel name the bot will look for to post mod-action logs.
MOD_LOG_CHANNEL_NAME = "mod-logs"

# --- Warnings ---
MAX_WARNINGS_BEFORE_ACTION = 3          # auto-action trigger
WARNING_AUTO_ACTION = "timeout"          # "timeout", "kick", or "ban"
WARNING_TIMEOUT_MINUTES = 60

# --- Automod: spam detection ---
SPAM_MESSAGE_LIMIT = 5        # max messages
SPAM_INTERVAL_SECONDS = 6     # ...within this many seconds
SPAM_TIMEOUT_MINUTES = 10

# --- Automod: mention spam ---
MAX_MENTIONS_PER_MESSAGE = 5

# --- Automod: caps filter ---
CAPS_MIN_LENGTH = 10           # only check messages at least this long
CAPS_PERCENT_THRESHOLD = 0.7   # 70%+ uppercase triggers filter

# --- Automod: banned words (simple substring filter; extend as needed) ---
BANNED_WORDS = [
    # add your own filtered terms here, lowercase
]

# --- Automod: invite link filter ---
BLOCK_DISCORD_INVITES = True
INVITE_WHITELIST_DOMAINS = [
    # e.g. "discord.gg/your-own-server-code"
]

# --- Roles exempt from automod (by name) ---
AUTOMOD_EXEMPT_ROLES = ["Moderator", "Admin"]
