import discord, os, requests, random, string, time, sqlite3
from datetime import datetime, timezone
from discord import AllowedMentions, Embed
from discord.ext import bridge
from discord.ext.bridge import BridgeOption
from dotenv import load_dotenv

load_dotenv()

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

intents = discord.Intents.default()
intents.message_content = True

bot = bridge.Bot(command_prefix=">", intents=intents)

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def flag_url(country_code: str) -> str:
    country_code = country_code.lower()
    return f"https://flagcdn.com/w160/{country_code}.png"

def fetch_api(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        time.sleep(delay)
    return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# @bot.bridge_command()
# async def help():
#

@bot.bridge_command(name="ping", description="Ping pong!")
async def ping(ctx: bridge.BridgeContext):
    await ctx.respond(f'Pong! Latency: {bot.latency}')

@bot.bridge_command(name="link", description="Link your Discord account to your RhythmTyper account")
async def link(ctx: bridge.BridgeContext, username: str):
    if not username:
        await ctx.respond("You must provide a username.", ephemeral=True)
        return

    discord_id = str(ctx.author.id)

    cursor.execute("SELECT username FROM linked_users WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    if row:
        linked_username = row[0]
        await ctx.respond(
            f"You already linked an account to `{linked_username}`. Unlink it to link a new account.",
            ephemeral=True
        )
        return

    data = fetch_api(
        f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/users/search?query={username}&limit=10")
    if not data:
        await ctx.respond("Failed to fetch user data from the API. Try again later.", ephemeral=True)
        return

    user_exists = False
    userid = None
    for user in data:
        if user["username"].lower() == username.lower():
            user_exists = True
            userid = user["userId"]
            break

    if not user_exists:
        await ctx.respond(f"No user found with username `{username}`.", ephemeral = True)
        return

    code = generate_code()
    expires_at = int(time.time()) + 300

    cursor.execute("""
    INSERT OR REPLACE INTO link_codes (discord_id, userid, code, expires_at)
    VALUES (?, ?, ?, ?)
    """, (discord_id, userid, code, expires_at))

    await ctx.respond(
        f"Your verification code: `{code}`. Put this in your RhythmTyper profile description and run `/verify`.",
        ephemeral=True)

@bot.bridge_command(name="verify", description="Verify code in description")
async def link_verify(ctx: bridge.BridgeContext):
    discord_id = str(ctx.author.id)

    cursor.execute("SELECT userid, code, expires_at FROM link_codes WHERE discord_id = ?", (discord_id,))
    row = cursor.fetchone()
    if not row:
        await ctx.respond("No pending verification found. Use `/link username` first.", ephemeral=True)
        return

    userid, code, expires_at = row

    if time.time() > expires_at:
        await ctx.respond("Your verification code expired. Generate a new one with `/link username`", ephemeral=True)
        cursor.execute("DELETE FROM link_codes WHERE discord_id = ?", (discord_id,))
        conn.commit()
        return

    profile_data = fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
    if not profile_data:
        await ctx.respond("Failed to fetch profile data. Try again later.", ephemeral=True)
        return

    profile_desc = profile_data.get("profileDescription", "")
    if code in profile_desc:
        cursor.execute("INSERT OR REPLACE INTO linked_users (discord_id, username, userid) VALUES (?, ?, ?)",
                       (discord_id, profile_data["username"], userid))
        cursor.execute("DELETE FROM link_codes WHERE discord_id = ?", (discord_id,))
        conn.commit()
        await ctx.respond(f"Successfully linked your account to `{profile_data['username']}`.", ephemeral=True)
    else:
        await ctx.respond("Verification code not found in profile description.", ephemeral=True)

@bot.bridge_command(name="unlink", description="Unlink your linked RhythmTyper account")
async def unlink(ctx: bridge.BridgeContext):
    discord_id = str(ctx.author.id)

    cursor.execute("DELETE from linked_users WHERE discord_id = ?", (discord_id,))
    conn.commit()

    if cursor.rowcount == 0:
        await ctx.respond("You don't have a linked account to unlink.", ephemeral = True)
    else:
        await ctx.respond("Successfully unlinked your account.", ephemeral = True)

@bot.bridge_command(name="rs", description="Get recent score of a RhythmTyper profile.")
async def rs(ctx: bridge.BridgeContext, user: discord.User = None):
    target = user if user is not None else ctx.author
    discord_id = str(target.id)

    cursor.execute(
        "SELECT userid FROM linked_users WHERE discord_id = ?",
        (discord_id,)
    )
    row = cursor.fetchone()

    if row is None:
        await ctx.respond(
            f"{target.mention} does not have a linked RhythmTyper account.",
            ephemeral = True,
            allowed_mentions=AllowedMentions.none()
        )
        return

    userid = row[0]

    profile_data = fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
    if not profile_data:
        await ctx.respond("Failed to fetch profile data. Try again later.", ephemeral=True)
        return

    recent_plays = profile_data['recentPlays']
    latest_play = max(recent_plays, key=lambda x: x['at'])
    print(latest_play)

    embed = Embed(
        title=latest_play['bt'],
        url=f"https://rhythmtyper.net/beatmap/{latest_play['bid']}",
        colour=discord.Colour.green()
    )

    embed.set_author(
        name=f"Total PP: {profile_data['totalPP']} {profile_data['username']} #{profile_data['globalRank']} ({profile_data['country']}#{profile_data['countryRank']})",
        icon_url=flag_url(profile_data['country']))

    embed.add_field(
        name="",
        value=f"Acc: {latest_play['acc']}"
    )



    await ctx.respond(embed=embed)

@bot.bridge_command(name="user", description="Get a RhythmTyper profile.")
async def user(ctx: bridge.BridgeContext, user: discord.User = None):
    target = user if user is not None else ctx.author
    discord_id = str(target.id)

    cursor.execute(
        "SELECT userid FROM linked_users WHERE discord_id = ?",
        (discord_id,)
    )
    row = cursor.fetchone()

    if row is None:
        await ctx.respond(
            f"{target.mention} does not have a linked RhythmTyper account.",
            ephemeral = True,
            allowed_mentions=AllowedMentions.none()
        )
        return

    userid = row[0]

    profile_data = fetch_api(f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/profile/{userid}")
    if not profile_data:
        await ctx.respond("Failed to fetch profile data. Try again later.", ephemeral=True)
        return

    rank_history = profile_data['rankHistory']

    peak_entry = min(rank_history, key=lambda x: x["rank"])
    peak_rank = peak_entry["rank"]
    peak_date = datetime.strptime(peak_entry["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)

    peak_text = f"Peak Rank: #{peak_rank} (<t:{int(peak_date.timestamp())}:R>)"

    embed = Embed(
        colour=discord.Colour.blurple()
    )
    embed.add_field(
        name="",
        value=
        f"**▸ Rank:** #{profile_data['globalRank']} ({profile_data['country']}#{profile_data['countryRank']})\n"
        f"**▸ Peak Rank:** {peak_text}\n"
        f"**▸ PP:** {round(profile_data['totalPP'], 2)} **Acc**: {round(profile_data['accuracy'], 2)}%\n"
        f"**▸ Playcount:** {profile_data['playCount']}\n"
        f"**▸ Ranks:** {profile_data['playCount']} ({round(profile_data['playTime'] / 3600, 2)} hrs)\n"
    )

    embed.set_author(name=f"RhythmTyper Profile for {profile_data['username']}",
                     icon_url=flag_url(profile_data['country']))

    print(profile_data)
    await ctx.respond(embed=embed)

@bot.bridge_command()
async def lb(
    ctx: bridge.BridgeContext,
    metric: str = bridge.BridgeOption(
        input_type=str,
        description="Metric to sort by",
        choices=["pp", "score"],
        required=False
    ),
     rank: int = bridge.BridgeOption(
         input_type=int,
         description="Get user with rank",
         required=False
     )
):
    if metric not in ["pp", "score"]:
        metric = "pp"

    sort_by = "totalPP" if metric == "pp" else "rankedScore"
    url = f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/leaderboard?limit=10&offset=0&sortBy={sort_by}"

    data = fetch_api(url)
    if not data:
        await ctx.respond("Failed to fetch leaderboard.", ephemeral=True)
        return

    print(data)

    if rank:
        await ctx.respond("Test 123")
    else:
        msg = "\n".join(
            f"{i + 1}. {entry['username']} — {round(entry['totalPP'], 2) if metric == 'pp' else entry['rankedScore']}"
            for i, entry in enumerate(data)
        )
        embed = Embed(
            colour=discord.Colour.purple()
        )
        embed.add_field(
            name="",
            value=
            f"{msg}"
        )

        await ctx.respond(embed=embed)

bot.run(os.getenv("BOT_TOKEN"))