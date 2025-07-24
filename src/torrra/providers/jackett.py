from typing import Any, cast

import httpx

from torrra._types import Torrent
from torrra.core.cache import CACHE_TTL, cache, make_cache_key


class JackettClient:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url: str = url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: int = timeout

    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        # jackett has build-in cache mechanism
        key = make_cache_key("jackett", query)

        if use_cache and key in cache:
            return cast(list[Torrent], cache[key])

        endpoint = f"{self.url}/api/v2.0/indexers/all/results"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            raw_results = resp.json().get("Results", [])
            results = [self._normalize_result(r) for r in raw_results]

        if use_cache:
            # cache.set might be missing type hints on set()
            cache.set(  # pyright: ignore[reportUnknownMemberType]
                key, results, expire=CACHE_TTL
            )

        return results

    async def validate(self) -> bool:
        url = f"{self.url}/api/v2.0/indexers/nonexistent_indexer/results"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                print(f"[error] could not connect to jackett at {self.url}.")
                print("please make sure jackett is running and the url is correct.")

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 401:
                    print("[error] invalid jackett api key.")
                    print("double-check the api key you provided.")
                elif status_code == 500 and "nonexistent_indexer" in e.response.text:
                    return True
                else:
                    print(f"[error] jackett returned http {status_code}.")
                    print("unexpected response from jackett. please verify your setup.")

            return False

    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("Title", ""),
            size=r.get("Size", 0),
            seeders=r.get("Seeders", 0),
            leechers=r.get("Peers", 0),
            source=r.get("Tracker", "unknown"),
            magnet_uri=r.get("MagnetUri", None),
        )
