from dataclasses import dataclass
from typing import Literal, TypedDict

# ========== TORRENTS ==========


@dataclass
class Torrent:
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str | None


class TorrentDict(TypedDict):
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str


# ========== INDEXERS ==========


IndexerName = Literal["jackett", "prowlarr"]


@dataclass
class Indexer:
    name: IndexerName
    url: str
    api_key: str
