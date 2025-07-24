from typing import Any, cast

import httpx

from torrra._types import Torrent, TorrentDict
from torrra.core.cache import get_cache, has_cache, make_cache_key, set_cache
from torrra.core.exceptions import JackettConnectionError


class JackettIndexer:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url: str = url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: int = timeout

    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        key = make_cache_key("jackett", query)

        if use_cache and has_cache(key):
            raw_data = cast(list[TorrentDict], get_cache(key))
            return [Torrent.from_dict(d) for d in raw_data]

        endpoint = f"{self.url}/api/v2.0/indexers/all/results"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            res = resp.json().get("Results", [])
            torrents = [self._normalize_result(r) for r in res]

        if use_cache:
            set_cache(key, [t.to_dict() for t in torrents])

        return torrents

    async def validate(self) -> bool:
        url = f"{self.url}/api/v2.0/indexers/nonexistent_indexer/results"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                raise JackettConnectionError(
                    f"could not connect to jackett at {self.url}\n"
                    + "please make sure jackett is running and the url is correct"
                )

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 401:
                    raise JackettConnectionError(
                        "invalid jackett api key\n"
                        + "double-check the api key you provided"
                    )
                elif status_code == 500 and "nonexistent_indexer" in e.response.text:
                    return True
                else:
                    raise JackettConnectionError(
                        f"jackett returned http {status_code}\n"
                        + "unexpected response from jackett. please verify your setup"
                    )

    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("Title", ""),
            size=r.get("Size", 0),
            seeders=r.get("Seeders", 0),
            leechers=r.get("Peers", 0),
            source=r.get("Tracker", "unknown"),
            magnet_uri=r.get("MagnetUri", None),
        )
