import os, asyncpg, time, asyncio
from utils.logger import info, error

_pool: asyncpg.pool.Pool | None = None

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
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetch(query: str, *args):
    if _pool is None:
        raise RuntimeError("Database not initialized")
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def execute(query: str, *args):
    if _pool is None:
        raise RuntimeError("Database not initialized")
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)

async def cleanup_link_codes():
    while True:
        try:
            await execute(
                "DELETE FROM link_codes WHERE expires_at < $1",
                int(time.time())
            )
            info("Expired link codes cleaned")
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            info("Link code cleanup task cancelled")
            raise
        except Exception as e:
            error(f"Link code cleanup failed: {e}")