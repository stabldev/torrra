from typing import Any, cast

import httpx

from torrra._types import Torrent, TorrentDict
from torrra.core.cache import get_cache, has_cache, make_cache_key, set_cache
from torrra.core.exceptions import ProwlarrConnectionError


class ProwlarrIndexer:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url: str = url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: int = timeout

    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        key = make_cache_key("prowlarr", query)

        if use_cache and has_cache(key):
            raw_data = cast(list[TorrentDict], get_cache(key))
            return [Torrent.from_dict(d) for d in raw_data]

        endpoint = f"{self.url}/api/v1/search"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            torrents = [self._normalize_result(r) for r in resp.json()]

        if use_cache:
            set_cache(key, [t.to_dict() for t in torrents])

        return torrents

    async def validate(self) -> bool:
        url = f"{self.url}/api/v1/health"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                raise ProwlarrConnectionError(
                    f"could not connect to prowlarr server\n"
                    + "please make sure prowlarr server is running and the url is correct"
                )

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 401:
                    raise ProwlarrConnectionError(
                        "invalid prowlarr server api key\n"
                        + "double-check the api key you provided"
                    )
                else:
                    raise ProwlarrConnectionError(
                        f"prowlarr server returned http {status_code}\n"
                        + "unexpected response from prowlarr server. please verify your setup"
                    )

    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("title", "unknown"),
            size=r.get("size", 0),
            seeders=r.get("seeders", 0),
            leechers=r.get("leechers", 0),
            source=r.get("indexer", "unknown"),
            magnet_uri=r.get("magnetUrl") or r.get("downloadUrl"),
        )
