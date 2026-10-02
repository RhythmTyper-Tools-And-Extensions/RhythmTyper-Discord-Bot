import discord
from discord.ext import bridge, commands

from utils.db import  execute, is_db_available

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(name="setdaily", description="Set what channel the daily map gets sent in.")
    @bridge.has_permissions(administrator=True)
    async def setdaily(self, ctx, channel: discord.TextChannel):
        message = await ctx.respond("Setting daily channel")

        if not channel:
            await message.edit("You must provide a channel.")
            return

        if not is_db_available():
            await message.edit(
                "Database is temporarily unavailable. Please try again later."
            )
            return

        await execute(
            """
            INSERT INTO daily_config (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2
            """,
            ctx.guild.id, channel.id
        )

        await message.edit(f"Daily map channel set to {channel.mention}")

    @bridge.bridge_command(name="setdailyping", description="Set what role should be pinged for daily maps.")
    @bridge.has_permissions(administrator=True)
    async def setdailyping(self, ctx, role: discord.Role):
        message = await ctx.respond("Setting daily ping role")

        if not role:
            await message.edit("You must provide a role.")
            return

        if not is_db_available():
            await message.edit(
                "Database is temporarily unavailable. Please try again later."
            )
            return

        await execute(
            """
            INSERT INTO daily_config (guild_id, role_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET role_id = $2
            """,
            ctx.guild.id, role.id
        )

        
        await message.edit(f"Daily role has been set {role.mention}")


def setup(bot):
    bot.add_cog(Admin(bot))