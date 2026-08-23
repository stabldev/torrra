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
    save_path: str | None


class TorrentStatus(TypedDict, total=False):
    """Torrent status on upload and download."""

    state: lt.torrent_status.states | int
    progress: float
    down_speed: float
    up_speed: float
    seeders: int
    total_seeders: int
    leechers: int
    peers: int
    total_peers: int
    is_paused: bool
    eta: float | None
    is_seeding: bool
    error: str | None
    error_file: int
    is_missing_files: bool
    is_queued: bool
    save_path: str


class TorrentRecord(TypedDict, total=False):
    """Torrent data stored in db."""

    magnet_uri: str
    title: str
    size: float
    source: str
    is_paused: bool
    is_notified: bool
    file_priorities: list[int] | None
    save_path: str | None


class SessionStats(TypedDict, total=False):
    """Session statistics for overall download/upload speeds and DHT."""

    download_rate: float
    upload_rate: float
    dht_nodes: int


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
    save_path: str | None = None

    @classmethod
    def from_dict(cls, d: TorrentDict) -> "Torrent":
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DownloadSelection:
    """Options confirmed before starting a torrent download."""

    file_priorities: list[int] | None
    save_path: str | None


# INDEXER TYPES
IndexerName = Literal["jackett", "prowlarr"]


@dataclass
class Indexer:
    """Indexer dataclass."""

    name: IndexerName
    url: str
    api_key: str
