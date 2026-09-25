import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

import config
from utils import database, modlog


def mod_check():
    """Requires the invoker to have kick_members permission (adjust as needed)."""
    async def predicate(ctx_or_interaction):
        return True
    return commands.check(predicate)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------------------------------------------
    # KICK
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("You can't kick someone with an equal or higher role than you.", ephemeral=True)
        if member == ctx.author:
            return await ctx.reply("You can't kick yourself.", ephemeral=True)

        try:
            await member.send(f"You were kicked from **{ctx.guild.name}**.\nReason: {reason}")
        except discord.Forbidden:
            pass

        await member.kick(reason=f"{reason} | Moderator: {ctx.author}")
        await ctx.reply(f"👢 Kicked **{member}**. Reason: {reason}")
        await modlog.send_log(
            ctx.guild, "Member Kicked", f"{member.mention} was kicked by {ctx.author.mention}",
            discord.Color.orange(), [("Reason", reason)]
        )

    # ---------------------------------------------------------------
    # BAN
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban", delete_days="Days of messages to delete (0-7)")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, delete_days: int = 0, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("You can't ban someone with an equal or higher role than you.", ephemeral=True)

        delete_days = max(0, min(delete_days, 7))

        try:
            await member.send(f"You were banned from **{ctx.guild.name}**.\nReason: {reason}")
        except discord.Forbidden:
            pass

        await member.ban(reason=f"{reason} | Moderator: {ctx.author}", delete_message_days=delete_days)
        await ctx.reply(f"🔨 Banned **{member}**. Reason: {reason}")
        await modlog.send_log(
            ctx.guild, "Member Banned", f"{member.mention} was banned by {ctx.author.mention}",
            discord.Color.red(), [("Reason", reason)]
        )

    # ---------------------------------------------------------------
    # UNBAN
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="unban", description="Unban a user by ID.")
    @app_commands.describe(user_id="The user ID to unban", reason="Reason for the unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            return await ctx.reply("Invalid user ID or user not found in ban list.", ephemeral=True)

        try:
            await ctx.guild.unban(user, reason=f"{reason} | Moderator: {ctx.author}")
        except discord.NotFound:
            return await ctx.reply("That user is not banned.", ephemeral=True)

        await ctx.reply(f"✅ Unbanned **{user}**.")
        await modlog.send_log(
            ctx.guild, "Member Unbanned", f"{user.mention} was unbanned by {ctx.author.mention}",
            discord.Color.green(), [("Reason", reason)]
        )

    # ---------------------------------------------------------------
    # TIMEOUT (mute) / UNTIMEOUT
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="timeout", description="Timeout (mute) a member for a duration in minutes.")
    @app_commands.describe(member="The member to timeout", minutes="Duration in minutes", reason="Reason")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("You can't timeout someone with an equal or higher role than you.", ephemeral=True)
        if minutes <= 0 or minutes > 40320:  # Discord max timeout is 28 days
            return await ctx.reply("Duration must be between 1 and 40320 minutes (28 days).", ephemeral=True)

        await member.timeout(timedelta(minutes=minutes), reason=f"{reason} | Moderator: {ctx.author}")
        await ctx.reply(f"🔇 Timed out **{member}** for {minutes} minute(s). Reason: {reason}")
        await modlog.send_log(
            ctx.guild, "Member Timed Out",
            f"{member.mention} was timed out by {ctx.author.mention} for {minutes}m",
            discord.Color.orange(), [("Reason", reason)]
        )

    @commands.hybrid_command(name="untimeout", description="Remove a member's timeout.")
    @app_commands.describe(member="The member to remove timeout from")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None, reason=f"Timeout removed by {ctx.author}")
        await ctx.reply(f"🔊 Removed timeout from **{member}**.")
        await modlog.send_log(
            ctx.guild, "Timeout Removed", f"{member.mention}'s timeout was removed by {ctx.author.mention}",
            discord.Color.green()
        )

    # ---------------------------------------------------------------
    # WARN / WARNINGS / CLEARWARNINGS
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="warn", description="Warn a member. Auto-escalates after repeated warnings.")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.bot:
            return await ctx.reply("You can't warn a bot.", ephemeral=True)

        count = database.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        await ctx.reply(f"⚠️ Warned **{member}** ({count}/{config.MAX_WARNINGS_BEFORE_ACTION}). Reason: {reason}")
        await modlog.send_log(
            ctx.guild, "Member Warned",
            f"{member.mention} was warned by {ctx.author.mention} ({count}/{config.MAX_WARNINGS_BEFORE_ACTION})",
            discord.Color.yellow(), [("Reason", reason)]
        )

        try:
            await member.send(f"You were warned in **{ctx.guild.name}**.\nReason: {reason}\nTotal warnings: {count}")
        except discord.Forbidden:
            pass

        if count >= config.MAX_WARNINGS_BEFORE_ACTION:
            await self._escalate(ctx, member, count)

    async def _escalate(self, ctx: commands.Context, member: discord.Member, count: int):
        action = config.WARNING_AUTO_ACTION
        reason = f"Automatic action: reached {count} warnings"
        try:
            if action == "timeout":
                await member.timeout(timedelta(minutes=config.WARNING_TIMEOUT_MINUTES), reason=reason)
                await ctx.send(f"🚨 **{member}** reached {count} warnings and was timed out for {config.WARNING_TIMEOUT_MINUTES}m.")
            elif action == "kick":
                await member.kick(reason=reason)
                await ctx.send(f"🚨 **{member}** reached {count} warnings and was kicked.")
            elif action == "ban":
                await member.ban(reason=reason)
                await ctx.send(f"🚨 **{member}** reached {count} warnings and was banned.")
            await modlog.send_log(ctx.guild, "Auto-Escalation Triggered", reason, discord.Color.dark_red())
        except discord.Forbidden:
            await ctx.send("⚠️ Tried to auto-escalate but I'm missing permissions.")

    @commands.hybrid_command(name="warnings", description="List a member's warnings.")
    @app_commands.describe(member="The member to check")
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        warns = database.get_warnings(ctx.guild.id, member.id)
        if not warns:
            return await ctx.reply(f"**{member}** has no warnings.")

        lines = []
        for i, w in enumerate(warns):
            mod = ctx.guild.get_member(w["moderator_id"])
            mod_name = mod.display_name if mod else w["moderator_id"]
            lines.append(f"`{i}` — {w['reason']} (by {mod_name}, {w['timestamp'][:10]})")

        embed = discord.Embed(
            title=f"Warnings for {member}",
            description="\n".join(lines),
            color=discord.Color.yellow(),
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="clearwarnings", description="Clear all warnings for a member.")
    @app_commands.describe(member="The member whose warnings will be cleared")
    @commands.has_permissions(manage_guild=True)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        database.clear_warnings(ctx.guild.id, member.id)
        await ctx.reply(f"🧹 Cleared all warnings for **{member}**.")
        await modlog.send_log(
            ctx.guild, "Warnings Cleared", f"{ctx.author.mention} cleared all warnings for {member.mention}",
            discord.Color.green()
        )

    @commands.hybrid_command(name="removewarning", description="Remove a single warning by its index.")
    @app_commands.describe(member="The member", index="The warning index shown by /warnings")
    @commands.has_permissions(manage_guild=True)
    async def removewarning(self, ctx: commands.Context, member: discord.Member, index: int):
        ok = database.remove_warning(ctx.guild.id, member.id, index)
        if ok:
            await ctx.reply(f"🧹 Removed warning `{index}` for **{member}**.")
        else:
            await ctx.reply("Invalid warning index.", ephemeral=True)

    # ---------------------------------------------------------------
    # PURGE
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="purge", description="Bulk delete messages in this channel.")
    @app_commands.describe(amount="Number of messages to delete (max 100)", member="Only delete messages from this member")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int, member: discord.Member = None):
        amount = max(1, min(amount, 100))

        def check(m):
            return member is None or m.author.id == member.id

        await ctx.defer(ephemeral=True) if ctx.interaction else None
        deleted = await ctx.channel.purge(limit=amount, check=check, before=ctx.message if not ctx.interaction else None)
        msg = f"🧹 Deleted {len(deleted)} message(s)."
        if ctx.interaction:
            await ctx.reply(msg, ephemeral=True)
        else:
            confirmation = await ctx.send(msg)
            await confirmation.delete(delay=4)

        await modlog.send_log(
            ctx.guild, "Messages Purged",
            f"{ctx.author.mention} deleted {len(deleted)} message(s) in {ctx.channel.mention}"
            + (f" from {member.mention}" if member else ""),
            discord.Color.orange()
        )

    # ---------------------------------------------------------------
    # SLOWMODE
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="slowmode", description="Set slowmode delay for this channel (seconds).")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int):
        seconds = max(0, min(seconds, 21600))
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.reply("🐇 Slowmode disabled.")
        else:
            await ctx.reply(f"🐌 Slowmode set to {seconds}s.")

    # ---------------------------------------------------------------
    # LOCK / UNLOCK
    # ---------------------------------------------------------------
    @commands.hybrid_command(name="lock", description="Lock this channel (prevent @everyone from sending messages).")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def lock(self, ctx: commands.Context, *, reason: str = "No reason provided"):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)
        await ctx.reply(f"🔒 Channel locked. Reason: {reason}")
        await modlog.send_log(ctx.guild, "Channel Locked", f"{ctx.channel.mention} locked by {ctx.author.mention}", discord.Color.orange())

    @commands.hybrid_command(name="unlock", description="Unlock this channel.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unlock(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.reply("🔓 Channel unlocked.")
        await modlog.send_log(ctx.guild, "Channel Unlocked", f"{ctx.channel.mention} unlocked by {ctx.author.mention}", discord.Color.green())

    # ---------------------------------------------------------------
    # Error handling for this cog (permission errors etc.)
    # ---------------------------------------------------------------
    @kick.error
    @ban.error
    @unban.error
    @timeout.error
    @untimeout.error
    @warn.error
    @warnings.error
    @clearwarnings.error
    @removewarning.error
    @purge.error
    @slowmode.error
    @lock.error
    @unlock.error
    async def moderation_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("🚫 You don't have permission to use this command.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("🚫 I don't have the required permissions to do that.", ephemeral=True)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("Couldn't find that member.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Missing argument: `{error.param.name}`.", ephemeral=True)
        else:
            await ctx.reply(f"⚠️ An error occurred: {error}", ephemeral=True)
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
