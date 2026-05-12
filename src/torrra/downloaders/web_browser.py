import webbrowser
from typing import Any

from typing_extensions import override

from torrra.downloaders.base import Downloader


class WebBrowserDownloader(Downloader):
    @override
    def send_magnet(self, magnet_uri: str, **kwargs: Any):
        webbrowser.open(magnet_uri)
