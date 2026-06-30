import asyncio
import random

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# T1: rate-limit + xoay User-Agent để tránh bị chặn
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
]

RATE_LIMIT_SECONDS = 5.0


class BlockedError(Exception):
    """Nguồn chặn (403/429) — pipeline log + alert + bỏ nguồn."""


class Fetcher:
    """httpx async client: 1 req / 5s, xoay UA, retry network lỗi tạm thời."""

    def __init__(self, rate_limit: float = RATE_LIMIT_SECONDS, timeout: float = 20.0):
        self._rate_limit = rate_limit
        self._client = httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers={}
        )
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "Fetcher":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        reraise=True,
    )
    async def get(self, url: str) -> str:
        # serialize + sleep để đảm bảo khoảng cách giữa các request
        async with self._lock:
            await asyncio.sleep(self._rate_limit)
            resp = await self._client.get(
                url, headers={"User-Agent": random.choice(USER_AGENTS)}
            )
        if resp.status_code in (403, 429):
            raise BlockedError(f"{resp.status_code} khi GET {url}")
        resp.raise_for_status()
        return resp.text
