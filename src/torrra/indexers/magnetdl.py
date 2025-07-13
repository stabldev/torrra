import asyncio
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from torrra.indexers.base import BaseIndexer
from torrra.types import Torrent


class Indexer(BaseIndexer):
    BASE_URL = "https://magnetdl.hair"

    def search(self, query: str, max_results: Optional[int] = None) -> List[Torrent]:
        normalized_query = quote_plus(query)
        url = f"{self.BASE_URL}/lmsearch?q={normalized_query}&cat=lmsearch"
        parser = self._get_parser(url)

        results = []
        urls = []

        nodes = parser.css("table tbody tr")
        for node in nodes:
            title_node = node.css_first("div.tt-name a")
            title = title_node.text(strip=True) if title_node else ""
            link = title_node.attributes.get("href") if title_node else ""
            size_node = node.css_first("td:nth-child(3)")
            size = size_node.text(strip=True) if size_node else ""

            if query not in title.lower() or link is None:
                continue

            results.append({"title": title, "size": size})
            urls.append(f"{self.BASE_URL}{link}")

            if max_results and len(results) >= max_results:
                break

        magnet_uris = asyncio.run(self._fetch_magnet_uris(urls))

        torrents: List[Torrent] = []
        for i, magnet_uri in enumerate(magnet_uris):
            if not magnet_uri:
                continue

            full_title = f"{results[i]['title']} {results[i]['size']}"
            torrents.append(Torrent(title=full_title, magnet_uri=magnet_uri))

        return torrents

    async def _fetch_magnet_uris(self, urls: List[str]):
        async def fetch(client: httpx.AsyncClient, url: str):
            try:
                res = await client.get(url, timeout=10)
                parser = HTMLParser(res.text)
                node = parser.css_first("ul.download-links-dontblock li a")
                return node.attributes.get("href") if node else ""
            except:
                return None

        async with httpx.AsyncClient() as client:
            tasks = [fetch(client, url) for url in urls]
            return await asyncio.gather(*tasks)
