import discord, time, config
from datetime import timedelta
from discord.ext import bridge, commands

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(name="ping")
    async def ping(self, ctx):
        await ctx.respond(f"pong! {round(self.bot.latency * 1000)}ms")

    @bridge.bridge_command(name="uptime")
    async def uptime(self, ctx):
        elapsed = int(time.time() - config.start_time)

        days, rem = divmod(elapsed, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        uptime_str = " ".join(parts)
        await ctx.respond(f"Bot uptime: {uptime_str}")

def setup(bot):
    bot.add_cog(Misc(bot))