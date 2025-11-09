from typing import Any, cast, override

import httpx

from torrra._types import Torrent, TorrentDict
from torrra.core.cache import cache
from torrra.core.exceptions import ProwlarrConnectionError
from torrra.indexers.base import BaseIndexer


class ProwlarrIndexer(BaseIndexer):
    @override
    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        key = cache.make_key("prowlarr", query)

        if use_cache and key in cache:
            raw_data = cast(list[TorrentDict], cache.get(key))
            return [Torrent.from_dict(d) for d in raw_data]

        endpoint = f"{self.url}/api/v1/search"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            torrents = [self._normalize_result(r) for r in resp.json()]

        if use_cache:
            cache.set(key, [t.to_dict() for t in torrents])

        return torrents

    @override
    async def healthcheck(self) -> bool:
        url = f"{self.url}/api/v1/health"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                raise ProwlarrConnectionError(
                    "could not connect to prowlarr server\n"
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

    @override
    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("title", "unknown"),
            size=r.get("size", 0),
            seeders=r.get("seeders", 0),
            leechers=r.get("leechers", 0),
            source=r.get("indexer", "unknown"),
            magnet_uri=r.get("magnetUrl") or r.get("downloadUrl"),
        )
