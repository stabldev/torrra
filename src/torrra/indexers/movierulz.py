import re
import asyncio
from typing import List, Tuple
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from torrra.indexers.base import BaseIndexer
from torrra.types import Torrent


class Indexer(BaseIndexer):
    BASE_URL = ""

    def search(self, query: str) -> List[Torrent]:
        normalized_query = quote_plus(query)
        url = f"https://www.5movierulz.voto/search_movies?s={normalized_query}"
        parser = self._get_parser(url)

        results = []

        has_no_results = parser.css_first("div.content ul h1")
        if has_no_results:
            return results

        titles_links: List[Tuple[str, str]] = []

        nodes = parser.css("div.content ul li")
        for node in nodes:
            title_node = node.css_first("p b")
            link_node = node.css_first("a")
            title = title_node.text() if title_node else ""
            link = link_node.attributes.get("href") if link_node else ""

            if query.lower() not in title.lower() or not link:
                continue

            titles_links.append((title, link))

        magnets_list = asyncio.run(self._fetch_magnet_uris(titles_links))

        for title, magnets in zip([t[0] for t in titles_links], magnets_list):
            for magnet in magnets:
                results.append(
                    Torrent(
                        title=f"{title} {magnet.title}", magnet_uri=magnet.magnet_uri
                    )
                )

        return results

    async def _fetch_magnet_uris(
        self, items: List[Tuple[str, str]]
    ) -> List[List[Torrent]]:
        async def fetch(client: httpx.AsyncClient, url: str):
            res = await client.get(url, timeout=10)
            parser = HTMLParser(res.text)

            results = []

            a_nodes = parser.css("div.entry-content p a")
            nodes = [
                node for node in a_nodes if "GET THIS TORRENT" in node.text(strip=True)
            ]

            for node in nodes:
                magnet_uri = node.attributes.get("href")
                if not magnet_uri:
                    continue

                title_node = node.css_first("small")
                title = title_node.text(strip=True) if title_node else ""
                formatted_title = re.sub(
                    r"\b(\d+(\.\d+)?)\s*(gb|mb|kb)\b",
                    lambda m: f"{m.group(1)} {m.group(3).upper()}",
                    title,
                )

                results.append(Torrent(title=formatted_title, magnet_uri=magnet_uri))

            return results

        async with httpx.AsyncClient() as client:
            tasks = [fetch(client, url) for (_, url) in items]
            return await asyncio.gather(*tasks)
