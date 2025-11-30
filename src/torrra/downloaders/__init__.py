from torrra.core.config import get_config
from torrra.downloaders.base import Downloader
from torrra.downloaders.internal import InternalDownloader
from torrra.downloaders.transmission import TransmissionDownloader
from torrra.downloaders.web_browser import WebBrowserDownloader


def get_downloader() -> Downloader:
    config = get_config()
    client = config.get("download.client", "internal")

    if client == "internal":
        return InternalDownloader()
    elif client == "transmission":
        return TransmissionDownloader()
    elif client == "web_browser":
        return WebBrowserDownloader()
    else:
        raise ValueError(f"Unknown downloader client: {client}")
