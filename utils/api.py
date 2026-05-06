import aiohttp, asyncio
from utils.logger import info, warn, error, debug

_session: aiohttp.ClientSession | None = None
_lock = asyncio.Lock()
_TIMEOUT = aiohttp.ClientTimeout(total=5)

async def get_session():
    global _session
    async with _lock:
        if _session is None or _session.closed:
            _session = aiohttp.ClientSession()
    return _session

async def close_api():
    global _session
    async with _lock:
        if _session and not _session.closed:
            await _session.close()
            debug("[API] ClientSession closed")
        _session = None

async def fetch_api(url: str, retries: int = 3, delay: float = 2.0):
    session = await get_session()
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=_TIMEOUT) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        debug(f"[API] Fetched {url} successfully")
                        return data
                    except (aiohttp.ContentTypeError, ValueError) as e:
                        warn(f"[API] Failed to parse JSON from {url}: {e}")
                        return None
                elif 400 <= resp.status < 500:
                    warn(f"[API] Client error {resp.status} for {url}, not retrying")
                    return None
                else:
                    warn(f"[API] Server error {resp.status} on attempt {attempt} for {url}, will retry")
        except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
            error(f"[API] HTTP error on attempt {attempt} for {url}: {e}")

        if attempt < retries:
            await asyncio.sleep(delay * (2 ** (attempt - 1)))

    error(f"[API] Failed to fetch {url} after {retries} attempts")
    return None