from dataclasses import dataclass
from typing import Literal


@dataclass
class Torrent:
    title: str
    magnet_uri: str


@dataclass
class Provider:
    name: Literal["Jackett"]
    url: str
    api_key: str
