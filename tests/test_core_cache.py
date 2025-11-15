from pathlib import Path
import pytest

from torrra.core.cache import Cache


@pytest.fixture
def cache(tmp_path: Path):
    # provides a cache instance that uses a temporary directory
    cache_dir = tmp_path / "test_cache"
    cache_instance = Cache(cache_dir)
    yield cache_instance
    cache_instance.close()


def test_make_key_consistency(cache: Cache):
    # tests that make_key produces a consistent hash for the same input
    key1 = cache.make_key("test_prefix", "my query")
    key2 = cache.make_key("test_prefix", "my query")
    assert key1 == key2
    assert key1.startswith("test_prefix:")


def test_make_key_uniqueness(cache: Cache):
    # tests that make_key produces different hashes for different inputs
    key1 = cache.make_key("prefix1", "query1")
    key2 = cache.make_key("prefix2", "query1")
    key3 = cache.make_key("prefix1", "query2")
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3
