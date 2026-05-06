import discord
from discord.ext import bridge, commands

from utils.api import fetch_api
from utils.cache import Cache

cache = Cache(ttl=300)

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(name="leaderboard", description="Show the RhythmTyper leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx, *args):
        message = await ctx.respond("Fetching leaderboard...")

        metric = "pp"
        rank = None
        range_start = None
        range_end = None
        country = None

        for arg in args:
            arg_lower = arg.lower()

            if arg_lower in ("pp", "score"):
                metric = arg_lower

            elif "-" in arg:
                parts = arg.split("-", 1)
                if not all(p.isdigit() for p in parts):
                    continue

                start, end = map(int, parts)

                if start >= end:
                    await message.edit("Invalid range: start must be less than end.")
                    return

                if end - start + 1 > 11:
                    await message.edit("Rank range can include **at most 11 entries**.")
                    return

                range_start = start
                range_end = end

            elif arg.isdigit():
                rank = int(arg)

            elif len(arg) == 2:
                country = arg.upper()


        if rank and range_start:
            await message.edit("You can specify **either a rank or a range**, not both.")
            return

        sort_by = "totalPP" if metric == "pp" else "rankedScore"


        if range_start:
            limit = range_end - range_start + 1
            offset = range_start - 1

        elif rank:
            limit = 50
            offset = ((rank - 1) // limit) * limit

        else:
            limit = 10
            offset = 0


        cache_key = f"{metric}:{country or 'global'}:{offset}:{limit}"
        data = cache.get(cache_key)

        if not data:
            url = (
                "https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/leaderboard"
                f"?limit={limit}&offset={offset}&sortBy={sort_by}"
            )
            if country:
                url += f"&country={country}"

            data = await fetch_api(url)
            if not data:
                await message.edit("Failed to fetch leaderboard.")
                return

            cache.set(cache_key, data)


        lines = []

        if rank:
            index = (rank - 1) % limit
            if index >= len(data):
                await message.edit(f"Rank {rank} not found.")
                return

            entry = data[index]
            value = (
                f"{round(entry['totalPP'], 2)} PP"
                if metric == "pp"
                else f"{entry['rankedScore']:,} Score"
            )
            lines.append(f"{rank}. {entry['username']} — {value}")

            title = f"{'Global' if not country else country} Rank {rank} ({metric.upper()})"

        else:
            start_rank = range_start if range_start else 1
            for i, entry in enumerate(data):
                actual_rank = start_rank + i
                value = (
                    f"{round(entry['totalPP'], 2)} PP"
                    if metric == "pp"
                    else f"{entry['rankedScore']:,} Score"
                )
                lines.append(f"{actual_rank}. {entry['username']} — {value}")

            title = (
                f"{'Global' if not country else country} "
                f"Leaderboard ({metric.upper()})"
            )

        embed = discord.Embed(colour=discord.Colour.purple())
        embed.add_field(name=title, value="\n".join(lines), inline=False)

        await message.edit(content=None, embed=embed)


def setup(bot):
    bot.add_cog(Leaderboard(bot))