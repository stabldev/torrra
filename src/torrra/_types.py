from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict

import libtorrent as lt


# TORRENT TYPES
class TorrentDict(TypedDict, total=False):
    """Dict variant of Torrent dataclass."""

    magnet_uri: str
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    file_priorities: list[int] | None


class TorrentStatus(TypedDict, total=False):
    """Torrent status on upload and download."""

    state: lt.torrent_status.states | int
    progress: float
    down_speed: float
    up_speed: float
    seeders: int
    leechers: int
    is_paused: bool
    eta: float | None
    is_seeding: bool
    error: str | None
    error_file: int
    is_missing_files: bool
    is_queued: bool


class TorrentRecord(TypedDict, total=False):
    """Torrent data stored in db."""

    magnet_uri: str
    title: str
    size: float
    source: str
    is_paused: bool
    is_notified: bool
    file_priorities: list[int] | None


@dataclass
class TorrentFileInfo:
    """Information for a single file in a torrent."""

    index: int
    path: str
    size: int


@dataclass
class Torrent:
    """Torrent I/O dataclass."""

    magnet_uri: str
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    file_priorities: list[int] | None = None

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
