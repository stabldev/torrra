import atexit
import hashlib

# no official stubs for diskcache
from diskcache import Cache  # pyright: ignore[reportMissingTypeStubs]
from platformdirs import user_cache_dir

CACHE_DIR = user_cache_dir("torrra")
CACHE_TTL = 300  # 5 mins

cache = Cache(CACHE_DIR)
atexit.register(cache.close)


def make_cache_key(prefix: str, query: str) -> str:
    return f"{prefix}:{hashlib.sha256(query.encode()).hexdigest()}"
