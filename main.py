import discord, os, random, string, time, aiohttp, asyncio, asyncpg
from datetime import datetime, timezone
from discord import AllowedMentions, Embed
from discord.ext import bridge, commands
from discord.ext.bridge import BridgeContext
from dotenv import load_dotenv

TOP_CACHE_TTL = 60
lb_cache = {
    "pp": {"top10": None, "timestamp": 0},
    "score": {"top10": None, "timestamp": 0}
}

grade_emojis = {
    "D": "<:D_:1458066183382368448>",
    "C": "<:C_:1458066166328328277>",
    "B": "<:B_:1458066143435554902>",
    "A": "<:A_:1458066125358370999>",
    "S": "<:S_:1458066106966347928>",
    "SS": "<:SS_:1458066072971382955>"
}

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = bridge.Bot(command_prefix=">", intents=intents)

async def get_pool():
    return await asyncpg.create_pool(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASS"),
        database=os.getenv("PG_DB"),
    )

pool = asyncio.get_event_loop().run_until_complete(get_pool())


def generate_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def flag_url(country_code: str) -> str:
    return f"https://flagcdn.com/w160/{country_code.lower()}.png"

async def get_top10(metric: str):
    now = time.time()
    cache_entry = lb_cache[metric]

    if cache_entry.get("top10") and now - cache_entry.get("timestamp", 0) < TOP_CACHE_TTL:
        return cache_entry["top10"], cache_entry["data"]

    sort_by = "totalPP" if metric == "pp" else "rankedScore"
    data = await fetch_api(
        f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/leaderboard?limit=50&offset=0&sortBy={sort_by}"
    )
    if not data:
        return None, None

    top_entries = data[:10]

    if metric == "pp":
        top_msg = "\n".join(
            f"{i+1}. {entry['username']} — PP: {round(entry['totalPP'], 2)}"
            for i, entry in enumerate(top_entries)
        )
    else:
        top_msg = "\n".join(
            f"{i+1}. {entry['username']} — Score: {entry['rankedScore']:,}"
            for i, entry in enumerate(top_entries)
        )

    cache_entry["top10"] = top_msg
    cache_entry["data"] = data
    cache_entry["timestamp"] = now

    return top_msg, data

async def fetch_api(url, retries=3, delay=2):
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, retries+1):
            try:
                async with session.get(url, timeout=5) as resp:
                    print(f"Fetching {url} -> Status {resp.status}")
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        print(f"Non-200 response: {resp.status}")
            except asyncio.TimeoutError:
                print(f"Timeout fetching {url}, attempt {attempt}")
            except aiohttp.ClientError as e:
                print(f"HTTP error fetching {url}, attempt {attempt}: {e}")
            await asyncio.sleep(delay)
    return None


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.respond("Command does not exist.", ephemeral=True)
    else:
        raise error

@bot.bridge_command(name="ping", description="Ping pong!")
async def ping(ctx: BridgeContext):
    await ctx.respond(f"Pong! Latency: {round(bot.latency*1000)} ms")


@bot.bridge_command(
    name="link", description="Link your Discord account to your RhythmTyper account"
)
async def link(ctx: BridgeContext, username: str = None):
    message = await ctx.respond("Fetching user...", ephemeral=True)

    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM link_codes WHERE expires_at < $1", int(time.time())
        )
        if not username:
            await message.edit("You must provide a username.")
            return
        
        discord_id = int(ctx.author.id)
        row = await conn.fetchrow(
            "SELECT username FROM linked_users WHERE discord_id = $1", discord_id
        )
        if row:
            await message.edit(
                f"You already linked an account to `{row['username']}`. Unlink it to link a new account.",
            )
            return
        data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/users/search?query={username}&limit=10"
        )
        if data is None:
            await message.edit(
                "Failed to fetch user data from the API. Try again later."
            )
            return

        userid = next((u["userId"] for u in data if u["username"].lower() == username.lower()), None)
        if userid is None:
            await message.edit(
                f"No user found with username `{username}`."
            )
            return

        code = generate_code()
        expires_at = int(time.time()) + 300
        await conn.execute(
            """
            INSERT INTO link_codes(discord_id, userid, code, expires_at)
            VALUES($1,$2,$3,$4)
            ON CONFLICT(discord_id) DO UPDATE
            SET userid = EXCLUDED.userid, code = EXCLUDED.code, expires_at = EXCLUDED.expires_at
        """,
            discord_id,
            userid,
            code,
            expires_at,
        )
        await message.edit(
            f"Your verification code: `{code}`. Put this in your RhythmTyper profile description and run `/verify`.",
        )


@bot.bridge_command(name="verify", description="Verify code in description")
async def link_verify(ctx: BridgeContext):
    message = await ctx.respond("Fetching user...", ephemeral=True)

    discord_id = int(ctx.author.id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT userid, code, expires_at FROM link_codes WHERE discord_id = $1",
            discord_id,
        )
        if not row:
            await message.edit(
                "No pending verification found. Use `/link username` first.",
            )
            return
        userid, code, expires_at = row["userid"], row["code"], row["expires_at"]
        if time.time() > expires_at:
            await conn.execute(
                "DELETE FROM link_codes WHERE discord_id = $1", discord_id
            )
            await message.edit(
                "Your verification code expired. Generate a new one with `/link username`",
            )
            return
        profile_data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}"
        )
        if not profile_data:
            await message.edit(
                "Failed to fetch profile data. Try again later."
            )
            return
        if code in profile_data.get("profileDescription", ""):
            await conn.execute(
                """
                INSERT INTO linked_users(discord_id, username, userid)
                VALUES($1,$2,$3)
                ON CONFLICT(discord_id) DO UPDATE
                SET username = EXCLUDED.username, userid = EXCLUDED.userid
            """,
                discord_id,
                profile_data["username"],
                userid,
            )
            await conn.execute(
                "DELETE FROM link_codes WHERE discord_id = $1", discord_id
            )
            await message.edit(
                f"Successfully linked your account to `{profile_data['username']}`.",
            )
        else:
            await message.edit(
                "Verification code not found in profile description."
            )


@bot.bridge_command(name="unlink", description="Unlink your linked RhythmTyper account")
async def unlink(ctx: BridgeContext):
    message = await ctx.respond("Unlinking account...", ephemeral=True)

    discord_id = int(ctx.author.id)
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM linked_users WHERE discord_id = $1", discord_id
        )
        if "0" in result:
            await message.edit(
                "You don't have a linked account to unlink."
            )
        else:
            await message.edit("Successfully unlinked your account.")


@bot.bridge_command(name="rs", description="Get recent score of a RhythmTyper profile.")
async def rs(ctx: BridgeContext, user: discord.User = None):
    target = user or ctx.author

    message = await ctx.respond("Fetching recent score...", ephemeral=True)

    discord_id = int(target.id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT userid FROM linked_users WHERE discord_id = $1", discord_id
        )
        if not row:
            await message.edit(
                f"{target.mention} does not have a linked RhythmTyper account.",
                allowed_mentions=AllowedMentions.none(),
            )
            return
        userid = row["userid"]
        profile_data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}"
        )
        if not profile_data:
            await message.edit(
                "Failed to fetch profile data. Try again later."
            )
            return
        recent_plays = profile_data.get("recentPlays", [])
        if not recent_plays:
            await message.edit("No recent plays found for this user.")
            return
        latest_play = max(recent_plays, key=lambda x: x["at"])
        play_time = datetime.fromisoformat(latest_play["at"].replace("Z", "+00:00"))
        emoji = grade_emojis.get(latest_play['gr'], "")
        mods = latest_play['mods']
        mod_text = "+NM" if not mods else "+" + "".join(mods)
        embed = Embed(
            title=latest_play["bt"],
            url=f"https://rhythmtyper.net/beatmap/{latest_play['bid']}",
            colour=discord.Colour.green(),
        )
        embed.set_author(
            name=f"{profile_data['username']}: {round(profile_data['totalPP'], 2)}pp {profile_data['username']} (#{profile_data['globalRank']} {profile_data['country']}#{profile_data['countryRank']})",
            icon_url=flag_url(profile_data["country"]),
        )
        embed.add_field(
            name="",
            value=f"{emoji} **{mod_text}\u2003{round(latest_play['acc'], 2)}%\u2003{latest_play['sc']:,}\u2003<t:{int(play_time.timestamp())}:R>**\n**{round(latest_play['pp'], 2)}pp\u2003combo: {latest_play['cb']}**"
        )

        print(latest_play)
        await message.edit(content=None, embed=embed)


@bot.bridge_command(name="user", description="Get a RhythmTyper profile.")
async def user(ctx: BridgeContext, user: discord.User = None):
    target = user or ctx.author

    message = await ctx.respond("Fetching user...", ephemeral=True)
    
    discord_id = int(target.id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT userid FROM linked_users WHERE discord_id = $1", discord_id
        )
        if not row:
            await message.edit(
                f"{target.mention} does not have a linked RhythmTyper account.",
                allowed_mentions=AllowedMentions.none(),
            )
            return
        userid = row["userid"]
        profile_data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}"
        )
        if not profile_data:
            await message.edit(
                "Failed to fetch profile data. Try again later."
            )
            return
        rank_history = profile_data.get("rankHistory", [])
        if rank_history:
            peak_entry = min(rank_history, key=lambda x: x["rank"])
            peak_rank = peak_entry["rank"]
            peak_date = datetime.strptime(peak_entry["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            peak_text = f"Peak Rank: #{peak_rank} (<t:{int(peak_date.timestamp())}:R>)"
        else:
            peak_text = "Peak Rank: N/A"
        embed = Embed(colour=discord.Colour.blurple())
        embed.add_field(
            name="",
            value=f"**▸ Rank:** #{profile_data['globalRank']} ({profile_data['country']}#{profile_data['countryRank']})\n**▸ Peak Rank:** {peak_text}\n**▸ PP:** {round(profile_data['totalPP'],2)} **Acc**: {round(profile_data['accuracy'],2)}%\n**▸ Playcount:** {profile_data['playCount']}\n**▸ Ranks:** {profile_data['playCount']} ({round(profile_data['playTime']/3600,2)} hrs)",
        )
        embed.set_author(
            name=f"RhythmTyper Profile for {profile_data['username']}",
            icon_url=flag_url(profile_data["country"]),
        )
        await message.edit(content=None, embed=embed)


@bot.bridge_command()
async def lb(ctx: BridgeContext, metric: str = None, rank: int = None):
    metric = metric.lower() if metric and metric.lower() in ["pp", "score"] else "pp"

    message = await ctx.respond("Fetching leaderboard...", ephemeral=True)

    top_msg, data = await get_top10(metric)
    if not top_msg:
        await message.edit("Failed to fetch leaderboard.")
        return

    if rank:
        if rank <= 50:
            entry = data[rank - 1]
        else:
            offset = ((rank - 1) // 50) * 50
            page_limit = 50
            page = await fetch_api(
                f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/leaderboard?limit={page_limit}&offset={offset}&sortBy={'totalPP' if metric=='pp' else 'rankedScore'}"
            )
            if not page or (rank - 1) % page_limit >= len(page):
                await message.edit(f"Rank {rank} not found.")
                return
            entry = page[(rank - 1) % page_limit]

        msg = f"{rank}. {entry['username']} — {round(entry['totalPP'],2)} PP" if metric == "pp" else f"{rank}. {entry['username']} — {entry['rankedScore']:,} Score"
        embed = Embed(colour=discord.Colour.purple())
        embed.add_field(name=f"Leaderboard ({metric.upper()})", value=msg)
        await message.edit(content=None, embed=embed)
        return

    embed = Embed(colour=discord.Colour.purple())
    embed.add_field(name=f"Top 10 Leaderboard ({metric.upper()})", value=top_msg)
    await message.edit(content=None, embed=embed)

bot.run(os.getenv("BOT_TOKEN"))