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

        if not is_db_available():
            await message.edit(
                "Database is temporarily unavailable. Please try again later.",
                ephemeral=True
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

def setup(bot):
    bot.add_cog(Admin(bot))