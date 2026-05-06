import os, asyncpg, time, asyncio
from utils.logger import info, error

_pool: asyncpg.pool.Pool | None = None
_db_available = True

def is_db_available():
    return _db_available

def set_db_available(value: bool):
    global _db_available
    _db_available = value

async def init_db():
    global _pool
    if _pool is not None:
        return _pool
    try:
        _pool = await asyncpg.create_pool(
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", 5432)),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASS"),
            database=os.getenv("PG_DB"),
            min_size=1,
            max_size=10
        )
        info("Database pool created")
        set_db_available(True)

        return _pool
    except Exception as e:
        error(f"Failed to initialize database pool: {e}")
        raise

async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        info("Database pool closed")

async def fetchrow(query: str, *args):
    if _pool is None:
        raise RuntimeError("Database not initialized")

    try:
        async with _pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    except Exception as e:
        set_db_available(False)
        raise

async def fetch(query: str, *args):
    if _pool is None:
        raise RuntimeError("Database not initialized")

    try:
        async with _pool.acquire() as conn:
            return await conn.fetch(query, *args)
    except Exception as e:
        set_db_available(False)
        raise

async def execute(query: str, *args):
    if _pool is None:
        raise RuntimeError("Database not initialized")

    try:
        async with _pool.acquire() as conn:
            return await conn.execute(query, *args)
    except Exception as e:
        set_db_available(False)
        raise

async def cleanup_link_codes():
    while True:
        if not is_db_available():
            await asyncio.sleep(60)
            continue

        try:
            await execute(
                "DELETE FROM link_codes WHERE expires_at < $1",
                int(time.time())
            )
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            info("Link code cleanup task cancelled")
            raise
        except Exception as e:
            error(f"Link code cleanup failed: {e}")