from typing import List
from selectolax.parser import HTMLParser

from torrra.types import Torrent
from torrra.helpers.html import parse_html
from abc import ABC, abstractmethod


class BaseIndexer(ABC):
    def _get_parser(self, url: str) -> HTMLParser:
        html = parse_html(url)
        return HTMLParser(html)

    @abstractmethod
    def search(self, query: str) -> List[Torrent]:
        pass
