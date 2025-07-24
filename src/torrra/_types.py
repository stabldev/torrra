from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict, cast


# TORRENT TYPES
class TorrentDict(TypedDict):
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str | None


@dataclass
class Torrent:
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str | None

    @classmethod
    def from_dict(cls, d: TorrentDict) -> "Torrent":
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# INDEXER TYPES
IndexerName = Literal["jackett", "prowlarr"]


@dataclass
class Indexer:
    name: IndexerName
    url: str
    api_key: str
