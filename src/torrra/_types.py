from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict

import libtorrent as lt


# TORRENT TYPES
class TorrentDict(TypedDict):
    """Dict variant of Torrent dataclass."""

    magnet_uri: str
    title: str
    size: float
    seeders: int
    leechers: int
    source: str


class TorrentStatus(TypedDict):
    """Torrent status on upload and download."""

    state: lt.torrent_status.states
    progress: float
    down_speed: float
    up_speed: float
    seeders: int
    leechers: int
    is_paused: bool
    eta: float | None
    is_seeding: bool


class TorrentRecord(TypedDict):
    """Torrent data stored in db."""

    magnet_uri: str
    title: str
    size: float
    source: str
    is_paused: bool
    is_notified: bool
    selected_files: list[int] | None


@dataclass
class Torrent:
    """Torrent I/O dataclass."""

    magnet_uri: str
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    selected_files: list[int] | None = None

    @classmethod
    def from_dict(cls, d: TorrentDict) -> "Torrent":
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TorrentFile:
    """A single file inside a torrent."""

    index: int
    path: str
    size: int


@dataclass(frozen=True)
class TorrentFileStatus:
    """Per-file download status inside a torrent."""

    index: int
    path: str
    size: int
    downloaded: int
    priority: int


# INDEXER TYPES
IndexerName = Literal["jackett", "prowlarr"]


@dataclass
class Indexer:
    """Indexer dataclass."""

    name: IndexerName
    url: str
    api_key: str
