from dataclasses import dataclass


@dataclass
class Torrent:
    title: str
    magnet_uri: str
