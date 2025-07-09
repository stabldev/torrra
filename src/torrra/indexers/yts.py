import asyncio
from typing import List

import httpx
from selectolax.parser import HTMLParser

from torrra.indexers.base import BaseIndexer
from torrra.types import Torrent


class Indexer(BaseIndexer):
    def search(self, query: str) -> List[Torrent]:
        url = f"https://yts.mx/browse-movies/{query}/all/all/0/latest/0/all"
        parser = self._get_parser(url)

        titles = []
        urls = []

        nodes = parser.css(
            "div.browse-content div.browse-movie-wrap div.browse-movie-bottom"
        )
        for node in nodes:
            title_node = node.css_first("a.browse-movie-title")
            year_node = node.css_first("div.browse-movie-year")

            title = title_node.text(strip=True) if title_node else ""
            link = title_node.attributes.get("href") if title_node else ""
            year = year_node.text(strip=True) if year_node else ""

            if query not in title.lower() or link is None:
                continue

            titles.append(f"{title} {year}")
            urls.append(link)

        magnets_list = asyncio.run(self._fetch_magnet_uris(urls))

        torrents = []
        for i, magnets in enumerate(magnets_list):
            for magnet in magnets:
                torrents.append(Torrent(title=f"{titles[i]} {magnet.title}", magnet_uri=magnet.magnet_uri))

        return torrents

    async def _fetch_magnet_uris(self, urls: List[str]) -> List[List[Torrent]]:
        async def fetch(client: httpx.AsyncClient, url: str):
            try:
                res = await client.get(url, timeout=10)
                parser = HTMLParser(res.text)
                results = []

                nodes = parser.css("div.modal div.modal-torrent")
                for node in nodes:
                    resolution_node = node.css_first("div.modal-quality span")
                    resolution = resolution_node.text(strip=True) if resolution_node else ""

                    quality_info = resolution

                    quality_size_nodes = node.css("p.quality-size")
                    if len(quality_size_nodes) >= 2:
                        source = quality_size_nodes[0].text(strip=True)
                        size = quality_size_nodes[1].text(strip=True)
                        quality_info = f"{source} {resolution} {size}"

                    magnet_node = node.css_first("a.magnet")
                    magnet_uri = magnet_node.attributes.get("href") if magnet_node else ""

                    if not magnet_uri:
                        continue

                    results.append(Torrent(title=quality_info, magnet_uri=magnet_uri))
                return results

            except Exception:
                return []

        async with httpx.AsyncClient() as client:
            tasks = [fetch(client, url) for url in urls]
            return await asyncio.gather(*tasks)
