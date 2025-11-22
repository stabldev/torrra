from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    import libtorrent as lt


# TORRENT TYPES
class TorrentDict(TypedDict):
    """Dict variant of Torrent dataclass."""

    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: str | None


class TorrentStatus(TypedDict):
    """Torrent status on upload and download."""

    state: lt.torrent_status.states
    progress: float
    down_speed: float
    up_speed: float
    seeders: int
    leechers: int


class TorrentRecord(TypedDict):
    """Torrent data stored in db."""

    magnet_uri: str
    title: str
    size: float
    source: str


@dataclass
class Torrent:
    """Torrent I/O dataclass."""

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
    """Indexer dataclass."""

    name: IndexerName
    url: str
    api_key: str
