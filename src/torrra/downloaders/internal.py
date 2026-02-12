from typing import Any

from typing_extensions import override

from torrra._types import Torrent
from torrra.core.torrent import get_torrent_manager
from torrra.downloaders.base import Downloader


class InternalDownloader(Downloader):
    @override
    def send_magnet(self, magnet_uri: str, **kwargs: Any):
        torrent = kwargs.get("torrent")
        if not isinstance(torrent, Torrent):
            raise TypeError("Torrent object is required for internal downloader")

        tm = get_torrent_manager()
        tm.add_torrent(torrent)
