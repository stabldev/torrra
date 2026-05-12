from abc import ABC, abstractmethod
from typing import Any


class Downloader(ABC):
    @abstractmethod
    def send_magnet(self, magnet_uri: str, **kwargs: Any):
        pass
