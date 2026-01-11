from discord.ext import commands
from utils.api import fetch_api
from utils.db import fetchrow

async def resolve_target(ctx, target: str = None):
    using_discord = False
    discord_id = None

    if target and target.startswith("<@") and target.endswith(">"):
        try:
            resolved_user = await commands.MemberConverter().convert(ctx, target)
            discord_id = resolved_user.id
            using_discord = True
        except commands.BadArgument:
            raise ValueError("Invalid Discord mention.")
    else:
        resolved_user = ctx.author
        if not target:
            discord_id = ctx.author.id
            using_discord = True

    userid = None
    username = None

    if using_discord:
        row = await fetchrow("SELECT userid, username FROM linked_users WHERE discord_id = $1", discord_id)
        if not row:
            raise ValueError(f"{resolved_user.mention} does not have a linked RhythmTyper account.")
        userid = row["userid"]
        username = row["username"]
    else:
        data = await fetch_api(
            f"https://us-central1-rhythm-typer.cloudfunctions.net/api/v2/users/search?query={target}&limit=1"
        )
        if not data:
            raise ValueError(f"No RhythmTyper user found with username `{target}`.")
        userid = data[0]["userId"]

    return {
        "discord_user": resolved_user,
        "userid": userid,
        "username": username
    }
