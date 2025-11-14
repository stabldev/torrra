from abc import ABC, abstractmethod
from typing import Any

from torrra._types import Torrent


class BaseIndexer(ABC):
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url: str = url.rstrip("/")
        self.api_key: str = api_key
        self.timeout: int = timeout

    @abstractmethod
    def get_search_url(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def get_healthcheck_url(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def search(self, query: str, use_cache: bool = True) -> list[Torrent]:
        raise NotImplementedError()

    @abstractmethod
    async def healthcheck(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def _normalize_result(self, r: dict[str, Any]) -> Torrent:
        raise NotImplementedError()
