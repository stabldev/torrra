from typing import Any

from transmission_rpc import Client
from typing_extensions import override

from torrra.core.config import get_config
from torrra.downloaders.base import Downloader


class TransmissionDownloader(Downloader):
    def __init__(self):
        config = get_config()
        self.host: str = config.get("downloaders.transmission.host", "localhost")
        self.port: int = config.get("downloaders.transmission.port", 9091)
        self.username: str = config.get("downloaders.transmission.username", "username")
        self.password: str = config.get("downloaders.transmission.password", "password")

    @override
    def send_magnet(self, magnet_uri: str, **kwargs: Any):
        client = Client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )
        client.add_torrent(magnet_uri)
