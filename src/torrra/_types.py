from dataclasses import dataclass


@dataclass
class Torrent:
    title: str
    magnet_uri: str


@dataclass
class Provider:
    name: str
    url: str
    api_key: str
