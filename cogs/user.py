import discord, time, string, random
from discord import Embed
from discord.ext import bridge, commands
from datetime import datetime, timezone

from config import grade_emojis

from utils.api import fetch_api
from utils.db import fetchrow, execute
from utils.logger import info, warn, error
from utils.resolve import resolve_target
from utils.flags import flag_url

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
            await ctx.respond(str(e), ephemeral=True)
            return

        userid = target_info["userid"]

        profile_data = await fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
        if not profile_data:
            await message.edit("Failed to fetch profile data. Try again later.", ephemeral=True)
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
        message = await ctx.respond("Fetching user...", ephemeral=True)

        try:
            target_info = await resolve_target(ctx, target)
        except ValueError as e:
            await ctx.respond(str(e), ephemeral=True)
            return

        userid = target_info["userid"]

        profile_data = await fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
        if not profile_data:
            await message.edit("Failed to fetch profile data. Try again later.", ephemeral=True)
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

        print(latest_play)

        embed = Embed(
            title=latest_play["bt"],
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
            value=f"**{round(latest_play['pp'], 2)}pp\u2003combo: {latest_play['cb']}**"

        )

        embed.set_footer(text="Mapset by")
        await message.edit(content=None, embed=embed)

def setup(bot):
    bot.add_cog(User(bot))