from typing import Any, cast

import httpx

from torrra._types import Torrent
from torrra.core.cache import CACHE_TTL, cache, make_cache_key


class ProwlarrClient:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url: str = url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: int = timeout

    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        key = make_cache_key("prowlarr", query)

        if use_cache and key in cache:
            return cast(list[Torrent], cache[key])

        endpoint = f"{self.url}/api/v1/search"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            results = [self._normalize_result(r) for r in resp.json()]

        if use_cache:
            # cache.set might be missing type hints on set()
            cache.set(  # pyright: ignore[reportUnknownMemberType]
                key, results, expire=CACHE_TTL
            )

        return results

    async def validate(self) -> bool:
        url = f"{self.url}/api/v1/health"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                print(f"[error] could not connect to prowlarr at {self.url}.")
                print("please make sure prowlarr is running and the url is correct.")

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 401:
                    print("[error] invalid prowlarr api key.")
                    print("double-check the api key you provided.")
                else:
                    print(f"[error] prowlarr returned http {status_code}.")
                    print(
                        "unexpected response from prowlarr. please verify your setup."
                    )

            return False

    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("title", ""),
            size=r.get("size", 0),
            seeders=r.get("seeders", 0),
            leechers=r.get("leechers", 0),
            source=r.get("indexer", "unknown"),
            magnet_uri=r.get("magnetUrl", None),
        )
