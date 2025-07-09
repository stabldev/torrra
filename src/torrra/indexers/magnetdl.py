from typing import List
from urllib.parse import quote_plus

from torrra.indexers.base import BaseIndexer
from torrra.types import Torrent

class Indexer(BaseIndexer):
    BASE_URL = "https://magnetdl.hair"

    def search(self, query: str) -> List[Torrent]:
        normalized_query = quote_plus(query)
        url = f"{self.BASE_URL}/lmsearch?q={normalized_query}&cat=lmsearch"
        parser = self._get_parser(url)

        res = []

        nodes = parser.css("table tbody tr")
        for node in nodes:
            title_node = node.css_first("div.tt-name a")
            title = title_node.text(strip=True) if title_node else ""
            link = title_node.attributes.get("href") if title_node else ""
            size_node = node.css_first("td:nth-child(3)")
            size = size_node.text(strip=True) if size_node else ""

            if query not in title.lower() or link is None:
                continue

            magnet_uri = self.get_magnet_uri(link)
            if not magnet_uri:
                continue

            torrent_title = f"{title} {size}"
            res.append(Torrent(title=torrent_title, magnet_uri=magnet_uri))

        return res

    def get_magnet_uri(self, link: str) -> str | None:
        url = self.BASE_URL + link
        parser = self._get_parser(url)

        magnet_uri_node = parser.css_first(".download-links-dontblock > li:nth-child(1) > a:nth-child(1)")
        magnet_uri = magnet_uri_node.attributes.get("href") if magnet_uri_node else ""

        return magnet_uri
