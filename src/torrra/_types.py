from dataclasses import dataclass
from typing import Literal


@dataclass
class Torrent:
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str | None


Indexers = Literal["jackett", "prowlarr"]


@dataclass
class Provider:
    name: Indexers
    url: str
    api_key: str
