import discord, time, string, random
from discord import Embed
from discord.ext import bridge, commands
from datetime import datetime, timezone

from discord.ext.bridge import BridgeContext

from config import grade_emojis

from utils.api import fetch_api
from utils.db import fetchrow, execute, is_db_available
from utils.logger import info, warn, error, debug
from utils.resolve import resolve_target
from utils.flags import flag_url
from utils.cache import Cache

lb_cache = Cache(ttl=300)

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_dm(self, ctx):
        if ctx.guild:
            await ctx.respond(
                "This command only works in DMs. Please message me directly.", ephemeral=True
            )
            return False
        return True

    @bridge.bridge_command(name="link", description="Link your RhythmTyper account")
    async def link(self, ctx, username: str = None):
        if not is_db_available():
            await ctx.respond(
                "Database is temporarily unavailable. Please try again later.",
                ephemeral=True
            )
            return

        if not await self.is_dm(ctx):
            return

        if not username:
            await ctx.respond("You must provide your RhythmTyper username.")
            return

        discord_id = ctx.author.id

        await execute("DELETE FROM link_codes WHERE expires_at < $1", int(time.time()))

        row = await fetchrow("SELECT username FROM linked_users WHERE discord_id = $1", discord_id)
        if row:
            await ctx.respond(
                f"You already linked an account: `{row['username']}`. Unlink first to link a new one.",
                ephemeral=True
            )
            return

        data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/users/search?query={username}&limit=1"
        )
        if not data:
            await ctx.respond("Failed to fetch user data. Try again later.", ephemeral=True)
            return

        userid = next((u["userId"] for u in data if u["username"].lower() == username.lower()), None)
        if not userid:
            await ctx.respond(f"No user found with username `{username}`.", ephemeral=True)
            return

        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        expires_at = int(time.time()) + 300

        await execute(
            """
            INSERT INTO link_codes(discord_id, userid, code, expires_at)
            VALUES($1, $2, $3, $4)
            ON CONFLICT(discord_id) DO UPDATE
            SET userid = EXCLUDED.userid, code = EXCLUDED.code, expires_at = EXCLUDED.expires_at
            """,
            discord_id, userid, code, expires_at
        )

        await ctx.respond(
            f"Your verification code: `{code}`\n"
            f"Put this in your RhythmTyper profile description, then run `/verify or >verify    ` in DMs.",
            ephemeral=True
        )

    @bridge.bridge_command(name="verify", description="Verify your code in profile description")
    async def verify(self, ctx):
        if not is_db_available():
            await ctx.respond(
                "Database is temporarily unavailable. Please try again later.",
                ephemeral=True
            )
            return

        if not await self.is_dm(ctx):
            return

        discord_id = ctx.author.id

        row = await fetchrow(
            "SELECT userid, code, expires_at FROM link_codes WHERE discord_id = $1",
            discord_id
        )
        if not row:
            await ctx.respond("No pending verification found. Use `/link <username>` first.", ephemeral=True)
            return

        userid, code, expires_at = row["userid"], row["code"], row["expires_at"]
        if time.time() > expires_at:
            await execute("DELETE FROM link_codes WHERE discord_id = $1", discord_id)
            await ctx.respond("Verification code expired. Generate a new one with `/link <username>`.", ephemeral=True)
            return

        profile_data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}"
        )
        if not profile_data:
            await ctx.respond("Failed to fetch profile data. Try again later.", ephemeral=True)
            return

        if code in profile_data.get("profileDescription", ""):
            await execute(
                """
                INSERT INTO linked_users(discord_id, username, userid)
                VALUES($1, $2, $3)
                ON CONFLICT(discord_id) DO UPDATE
                SET username = EXCLUDED.username, userid = EXCLUDED.userid
                """,
                discord_id, profile_data["username"], userid
            )
            await execute("DELETE FROM link_codes WHERE discord_id = $1", discord_id)
            await ctx.respond(f"Successfully linked to `{profile_data['username']}`!", ephemeral=True)
        else:
            await ctx.respond("Verification code not found in your profile description.", ephemeral=True)

    @bridge.bridge_command(name="unlink", description="Unlink your linked RhythmTyper account")
    async def unlink(self, ctx):
        if not is_db_available():
            await ctx.respond(
                "Database is temporarily unavailable. Please try again later.",
                ephemeral=True
            )
            return

        if not await self.is_dm(ctx):
            return

        discord_id = ctx.author.id
        result = await execute("DELETE FROM linked_users WHERE discord_id = $1", discord_id)
        if "0" in result:
            await ctx.respond("You don't have a linked account.", ephemeral=True)
        else:
            await ctx.respond("Successfully unlinked your account.", ephemeral=True)

    @bridge.bridge_command(name="status")
    async def status(self, ctx):
        if not is_db_available():
            await ctx.respond(
                "Database is temporarily unavailable. Please try again later.",
                ephemeral=True
            )
            return

        if not await self.is_dm(ctx):
            return

        discord_id = ctx.author.id

        linked = await fetchrow(
            "SELECT username FROM linked_users WHERE discord_id = $1",
            discord_id
        )

        pending = await fetchrow(
            "SELECT expires_at FROM link_codes WHERE discord_id = $1",
            discord_id
        )

        if linked:
            await ctx.respond(f"Linked account: `{linked['username']}`")
            return

        if pending:
            remaining = pending["expires_at"] - int(time.time())
            await ctx.respond(f"Pending verification. Expires in {remaining}s")
            return

        await ctx.respond("No linked account and no pending verification.")

    @bridge.bridge_command(name="user", description="Display a users profile")
    async def user(self, ctx, target: str = None):
        message = await ctx.respond("Fetching user...", ephemeral=True)

        try:
            target_info = await resolve_target(ctx, target)
        except ValueError as e:
            await message.edit(str(e))
            return

        userid = target_info["userid"]

        profile_data = await fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
        if not profile_data:
            await message.edit("Failed to fetch profile data. Try again later.")
            return

        current_rank = profile_data['globalRank']
        current_date = datetime.now(timezone.utc)

        row = await fetchrow("SELECT peak_rank, achieved_at FROM user_peak WHERE userid=$1", userid)
        db_peak_rank = row["peak_rank"] if row else None
        db_peak_date = row["achieved_at"] if row else None

        all_candidates = [{"rank": current_rank, "date": current_date}]
        all_candidates.extend(profile_data['rankHistory'])
        if db_peak_rank is not None:
            all_candidates.append({"rank": db_peak_rank, "date": db_peak_date})

        best_entry = min(all_candidates, key=lambda x: x['rank'])
        peak_rank = best_entry['rank']
        peak_date = best_entry['date']

        if isinstance(peak_date, str):
            peak_date = datetime.fromisoformat(peak_date).replace(tzinfo=timezone.utc)

        if db_peak_rank != peak_rank:
            await execute(
                """
                INSERT INTO user_peak(userid, peak_rank, achieved_at)
                VALUES($1, $2, $3)
                ON CONFLICT(userid) DO UPDATE
                SET peak_rank = EXCLUDED.peak_rank,
                    achieved_at = EXCLUDED.achieved_at
                """,
                userid, peak_rank, peak_date
            )

        peak_text = f"Peak Rank: #{peak_rank} (<t:{int(peak_date.timestamp())}:R>)"

        embed = Embed(colour=discord.Colour.blurple())
        embed.set_author(
            name=f"{profile_data['username']}",
            url=f"https://rhythmtyper.net/user/{profile_data['userId']}",
            icon_url=flag_url(profile_data["country"])
        )

        embed.add_field(
            name="",
            value=(
                f"**▸ Rank:** #{current_rank} ({profile_data['country']}#{profile_data['countryRank']})\n"
                f"**▸ Peak Rank:** {peak_text}\n"
                f"**▸ PP:** {round(profile_data['totalPP'], 2)} | **Acc:** {round(profile_data['accuracy'], 2)}%\n"
                f"**▸ Playcount:** {profile_data['playCount']} ({round(profile_data['playTime']/3600, 2)} hrs)"
            )
        )

        embed.set_thumbnail(url=f"https://firebasestorage.googleapis.com/v0/b/rhythm-typer.firebasestorage.app/o/profile-pictures%2F{userid}.jpeg?alt=media")

        await message.edit(content=None, embed=embed)

    @bridge.bridge_command(name="recent", description="Show recent score by user", aliases=["rs"])
    async def recent(self, ctx, target: str = None):
        message = await ctx.respond("Fetching recent score...", ephemeral=True)

        try:
            target_info = await resolve_target(ctx, target)
        except ValueError as e:
            await message.edit(str(e))
            return

        userid = target_info["userid"]

        profile_data = await fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
        if not profile_data:
            await message.edit("Failed to fetch profile data. Try again later.")
            return

        recent_plays = profile_data.get("recentPlays", [])
        if not recent_plays:
            await message.edit(content="No recent plays found for this user.")
            return

        latest_play = max(recent_plays, key=lambda x: x["at"])
        play_time = datetime.fromisoformat(latest_play["at"].replace("Z", "+00:00"))
        emoji = grade_emojis.get(latest_play['gr'], "")
        mods = latest_play['mods']
        mod_text = "+NM" if not mods else "+" + "".join(mods)
        total_seconds = int(latest_play['len'])
        minutes, seconds = divmod(total_seconds, 60)
        length_fmt = f"{minutes}:{seconds:02d}"

        embed = Embed(
            title=f"{latest_play['bt']} [{latest_play['sr']:.2f}★]",
            url=f"https://rhythmtyper.net/beatmap/{latest_play['bid']}",
            colour=discord.Colour.green(),
        )
        embed.set_author(
            name=f"{profile_data['username']}: {round(profile_data['totalPP'], 2)}pp "
                 f"(#{profile_data['globalRank']} {profile_data['country']}#{profile_data['countryRank']})",
            icon_url=flag_url(profile_data["country"]),
            url=f"https://rhythmtyper.net/user/{profile_data['userId']}",
        )
        embed.add_field(
            name=f"{emoji} {mod_text}\u2003{latest_play['sc']:,}\u2003{round(latest_play['acc'], 2)}%\u2003<t:{int(play_time.timestamp())}:R>",
            value=f"**{round(latest_play['pp'])}**pp • ({latest_play['pf']}/{latest_play['gd']}/{latest_play['ok']}/{latest_play['ms']}) • **{latest_play['cb']}x**/{latest_play['pf'] + latest_play['gd'] + latest_play['ok'] + latest_play['ms']}x\n"
            f"`{length_fmt}` • `OD: {latest_play['od']}`• BPM: {latest_play['bpm']}"
        )

        embed.set_footer(text=f"Mapset by {latest_play['mn']}")
        await message.edit(content=None, embed=embed)

    @bridge.bridge_command(name="whatif")
    async def whatif(self, ctx, pp: int = None, target: str = None):
        message = await ctx.respond("Fetching data...", ephemeral=True)

        if pp is None:
            await message.edit("You must provide a PP value for >whatif.")
            return

        try:
            target_info = await resolve_target(ctx, target)
        except ValueError as e:
            await message.edit(str(e))
            return

        userid = target_info["userid"]

        profile_data = await fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
        if not profile_data:
            await message.edit("Failed to fetch profile data. Try again later.")
            return

        top_plays = profile_data.get("topPlays", [])
        if not top_plays:
            await message.edit(content="No top plays found for this user.")
            return

        placement = len(top_plays) + 1
        sorted_plays = sorted(top_plays, key=lambda x: x['pp'], reverse=True)

        for i, top_play in enumerate(sorted_plays, start=1):
            if pp > top_play['pp']:
                placement = i
                break

        decay = 0.95
        max_plays = 100

        new_top = sorted_plays.copy()
        new_top.insert(placement - 1, {'pp': pp})
        new_top = new_top[:max_plays]

        if new_top:
            new_total_pp = new_top[0]['pp']
            for i, p in enumerate(new_top[1:], start=1):
                new_total_pp += p['pp'] * (decay ** i)
        else:
            new_total_pp = 0

        pp_change = new_total_pp - profile_data['pp']

        cache_key = "top500_global_pp"
        cached = lb_cache.get(cache_key)
        if not cached:
            cached = {
                "data": [],
                "fetched_until": 0
            }

        lb_data = cached["data"]

        approx_rank = None
        limit = 500

        offset = cached["fetched_until"]
        checked_until = 0

        while offset < limit:
            if len(lb_data) <= offset:
                page = await fetch_api(
                    f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/leaderboard?limit=50&offset={offset}&sortBy=totalPP"
                )
                if not page:
                    break

                lb_data.extend(page)
                offset += len(page)

                cached["fetched_until"] = offset
                lb_cache.set(cache_key, cached)

            while checked_until < len(lb_data):
                if new_total_pp >= lb_data[checked_until]["totalPP"]:
                    approx_rank = checked_until + 1
                    break
                checked_until += 1

            if approx_rank is not None:
                break
        if approx_rank is None:
            if cached["fetched_until"] >= limit:
                approx_rank = ">500"
            else:
                approx_rank = "Unknown"

        embed = Embed(colour=discord.Colour.blurple())
        embed.set_author(
            name=f"{profile_data['username']}",
            url=f"https://rhythmtyper.net/user/{profile_data['userId']}",
            icon_url=flag_url(profile_data["country"])
        )

        embed.add_field(name=f"What if {profile_data['username']} got a new {pp}pp score?", value=f"A {pp}pp score would be {profile_data['username']} **#{placement}** best play.\nTheir pp would change by {round(pp_change, 2)} to {round(profile_data['pp'] + pp_change, 2)}pp\nThey would reach approx. rank **#{approx_rank}**")

        await message.edit(content="", embed=embed)


def setup(bot):
    bot.add_cog(User(bot))