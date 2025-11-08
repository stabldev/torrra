import atexit
import hashlib
from typing import Any, cast

# no official stubs for diskcache
from diskcache import Cache
from platformdirs import user_cache_dir

from torrra.core.constants import CACHE_TTL

cache = Cache(user_cache_dir("torrra"))
atexit.register(cache.close)

# ========== CACHE FUNCTIONS ========== #


def has_cache(key: str) -> bool:
    return key in cache


def get_cache(key: str) -> Any:
    return cast(Any, cache[key])


def set_cache(key: str, value: Any, expire: int = CACHE_TTL) -> None:
    cache.set(key, value, expire=expire)


def delete_cache(key: str) -> None:
    if key in cache:
        del cache[key]


# ========== CACHE UTILS ========== #


def make_cache_key(prefix: str, query: str) -> str:
    return f"{prefix}:{hashlib.sha256(query.encode()).hexdigest()}"
