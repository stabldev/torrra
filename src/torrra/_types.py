from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Torrent:
    title: str
    size: float
    seeders: int
    leechers: int
    source: str
    magnet_uri: Optional[str]


@dataclass
class Provider:
    name: Literal["Jackett"]
    url: str
    api_key: str
