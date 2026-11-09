import atexit
import hashlib
from typing import Any

from diskcache_community import Cache as _Cache
from diskcache_community import SafeDisk
from platformdirs import user_cache_dir
from typing_extensions import override

from torrra.core.config import get_config
from torrra.core.constants import DEFAULT_CACHE_TTL


class Cache(_Cache):
    @override
    def set(
        self,
        key: str,
        value: Any,
        expire: float | None = None,
        read: bool = False,
        tag: Any = None,
        retry: bool = False,
    ):
        expire = get_config().get("general.cache_ttl", DEFAULT_CACHE_TTL)
        return super().set(key, value, expire, read, tag, retry)

    def make_key(self, prefix: str, query: str) -> str:
        return f"{prefix}:{hashlib.sha256(query.encode()).hexdigest()}"


cache = Cache(user_cache_dir("torrra"), disk=SafeDisk.with_options(on_error="miss"))
atexit.register(cache.close)
