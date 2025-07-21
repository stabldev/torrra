from typing import Dict, List, cast

import httpx

from torrra._types import Torrent
from torrra.core.cache import CACHE_TTL, cache, make_cache_key


class ProwlarrClient:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, use_cache: bool = True) -> List[Torrent]:
        key = make_cache_key("prowlarr", query)

        if use_cache and key in cache:
            return cast(List[Torrent], cache[key])

        endpoint = f"{self.url}/api/v1/search"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            results = [self._normalize_result(r) for r in resp.json()]

        if use_cache:
            cache.set(key, results, expire=CACHE_TTL)

        return results

    def _normalize_result(self, r: Dict) -> Torrent:
        return Torrent(
            title=r.get("title", ""),
            size=r.get("size", 0),
            seeders=r.get("seeders", 0),
            leechers=r.get("leechers", 0),
            source=r.get("indexer", "unknown"),
            magnet_uri=r.get("magnetUrl", None),
        )
