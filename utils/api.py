import aiohttp, asyncio
from utils.logger import info, warn, error, debug

_session: aiohttp.ClientSession | None = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

async def close_api():
    global _session
    if _session and not _session.closed:
        await _session.close()
        debug("[API] ClientSession closed")
    _session = None

async def fetch_api(url: str, retries: int = 3, delay: float = 2.0):
    session = await get_session()
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    debug(f"[API] Fetched {url} successfully")
                    return data
                else:
                    warn(f"[API] Non-200 response ({resp.status}) for {url}")
        except asyncio.TimeoutError:
            warn(f"[API] Timeout on attempt {attempt} for {url}")
        except aiohttp.ClientError as e:
            error(f"[API] HTTP error on attempt {attempt} for {url}: {e}")
        await asyncio.sleep(delay)
    error(f"[API] Failed to fetch {url} after {retries} attempts")
    return None