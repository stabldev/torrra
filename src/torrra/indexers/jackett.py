from typing import Any, cast
from typing_extensions import override

import httpx

from torrra._types import Torrent, TorrentDict
from torrra.core.cache import cache
from torrra.core.exceptions import IndexerError
from torrra.indexers.base import BaseIndexer


class JackettIndexer(BaseIndexer):
    @override
    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        key = cache.make_key("jackett", query)

        if use_cache and key in cache:
            raw_data = cast(list[TorrentDict], cache.get(key))
            return [Torrent.from_dict(d) for d in raw_data]

        endpoint = f"{self.url}/api/v2.0/indexers/all/results"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            res = resp.json().get("Results", [])
            torrents = [self._normalize_result(r) for r in res]

        if use_cache and torrents:
            cache.set(key, [t.to_dict() for t in torrents])

        return torrents

    @override
    async def healthcheck(self) -> bool:
        url = f"{self.url}/api/v2.0/indexers/nonexistent_indexer/results"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True

            except httpx.RequestError:
                raise IndexerError(
                    "could not connect to jackett server\n"
                    + "please make sure jackett server is running and the url is correct"
                )

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if status_code == 401:
                    raise IndexerError(
                        "invalid jackett server api key\n"
                        + "double-check the api key you provided"
                    )
                elif status_code == 500 and "nonexistent_indexer" in e.response.text:
                    return True
                else:
                    raise IndexerError(
                        f"jackett server returned http {status_code}\n"
                        + "unexpected response from jackett server. please verify your setup"
                    )

    @override
    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        return Torrent(
            title=r.get("Title", "unknown"),
            size=r.get("Size", 0),
            seeders=r.get("Seeders", 0),
            leechers=r.get("Peers", 0),
            source=r.get("Tracker", "unknown"),
            magnet_uri=r.get("MagnetUri") or r.get("Link"),
        )
