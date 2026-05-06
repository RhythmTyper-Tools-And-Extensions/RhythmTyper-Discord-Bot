import discord, dotenv, os, platform, signal, asyncio
from discord.ext.bridge import Bot
from utils.logger import info, warn, error, debug
from utils.db import init_db, close_db, cleanup_link_codes
from utils.api import close_api
from asyncio import Task
from typing import Optional

shutdown_called = False
cleanup_task: Optional[Task] = None


dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(command_prefix=">", intents=intents)

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{filename[:-3]}")
            info(f"Loaded cog: {filename}")
        except Exception as e:
            error(f"Failed to load cog {filename}: {e}")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[90m"
ACCENT = "\033[96m"

@bot.event
async def on_ready():
    global cleanup_task

    try:
        await init_db()
    except Exception as e:
        warn(f"Database unavailable on startup: {e}")

    from utils.db import _pool
    if _pool:
        cleanup_task = bot.loop.create_task(cleanup_link_codes())

    latency = round(bot.latency * 1000)
    users = sum(g.member_count or 0 for g in bot.guilds)

    info("Bot started")

    print()
    print(f"{BOLD}[READY]{RESET} {bot.user}")
    print()

    def row(label, value):
        print(f"  {DIM}{label:<10}{RESET}: {value}")

    row("Servers", len(bot.guilds))
    row("Users", users)
    row("Latency", f"{latency} ms")

    print()
    row("Python", platform.python_version())
    row("py-cord", discord.__version__)
    row("Platform", f"{platform.system()} {platform.release()}")
    print()


async def shutdown():
    global shutdown_called
    if shutdown_called:
        return
    shutdown_called = True

    info("Shutting down...")

    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    try:
        from utils.api import _session, close_api
        if _session and not _session.closed:
            await close_api()
    except Exception:
        pass

    try:
        from utils.db import _pool, close_db
        if _pool:
            await close_db()
    except Exception:
        pass

    await bot.close()


try:
    bot.run(os.getenv("TOKEN"))
except discord.LoginFailure:
    error("Invalid token. Check your main.env file.")
except Exception as e:
    error(f"Bot failed to start: {e}")