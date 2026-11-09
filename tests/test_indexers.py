from pathlib import Path
from typing import Any

import pytest
import respx
from diskcache_community import Disk
from httpx import Response

from torrra.core import cache as cache_module
from torrra.core.cache import Cache
from torrra.indexers.base import BaseIndexer
from torrra.indexers.jackett import JackettIndexer
from torrra.indexers.prowlarr import ProwlarrIndexer

MOCK_API_URL = "http://mock.indexer.url"
MOCK_API_KEY = "mock_api_key"

MOCK_SEARCH_RESPONSE = {
    "jackett": {
        "Results": [
            {
                "Title": "Arch Linux ISO (Mock)",
                "Size": 840499200,
                "Seeders": 523,
                "Peers": 17,
                "Tracker": "MockIndexer",
                "MagnetUri": "magnet:?xt=urn:btih:mock",
            }
        ]
    },
    "prowlarr": [
        {
            "title": "Arch Linux ISO (Mock)",
            "size": 840499200,
            "seeders": 523,
            "leechers": 17,
            "indexer": "MockIndexer",
            "magnetUrl": "magnet:?xt=urn:btih:mock",
        }
    ],
}


# indexers annotate these fields as ints but send explicit nulls: jackett
# reports "Peers": null for several trackers, and prowlarr omits counts for
# indexers that don't publish them
MOCK_NULL_RESPONSE = {
    "jackett": {
        "Results": [
            {
                "Title": None,
                "Size": None,
                "Seeders": None,
                "Peers": None,
                "Tracker": None,
                "MagnetUri": None,
                "Link": "http://mock.indexer.url/dl/mock",
            }
        ]
    },
    "prowlarr": [
        {
            "title": None,
            "size": None,
            "seeders": None,
            "leechers": None,
            "indexer": None,
            "magnetUrl": None,
            "downloadUrl": "http://mock.indexer.url/dl/mock",
        }
    ],
}


@pytest.fixture(params=[JackettIndexer, ProwlarrIndexer])
def indexer(request: pytest.FixtureRequest) -> BaseIndexer:
    return request.param(url=MOCK_API_URL, api_key=MOCK_API_KEY)


@respx.mock
@pytest.mark.parametrize("query", ["arch linux iso"])
async def test_search(indexer: BaseIndexer, query: str) -> None:
    indexer_name = indexer.__class__.__name__.removesuffix("Indexer").lower()
    mock_body = MOCK_SEARCH_RESPONSE[indexer_name]

    url = indexer.get_search_url()
    respx.get(url).mock(Response(200, json=mock_body))

    results = await indexer.search(query, use_cache=False)

    assert results is not None
    assert len(results) == 1
    r = results[0]
    assert r.title == "Arch Linux ISO (Mock)"
    assert r.size == 840499200
    assert r.seeders == 523
    assert r.leechers == 17
    assert r.source == "MockIndexer"
    assert r.magnet_uri is not None
    assert r.magnet_uri.startswith("magnet:")


@respx.mock
async def test_healthcheck(indexer: BaseIndexer) -> None:
    url = indexer.get_healthcheck_url()
    respx.get(url).mock(Response(200))

    assert await indexer.healthcheck() is True


@respx.mock
async def test_null_fields_are_coerced(indexer: BaseIndexer) -> None:
    """A null in a numeric field must not reach Torrent.

    dict.get(key, default) returns the null when the key is present, so the
    defaults these normalizers were written with never fired.
    """
    indexer_name = indexer.__class__.__name__.removesuffix("Indexer").lower()
    respx.get(indexer.get_search_url()).mock(
        Response(200, json=MOCK_NULL_RESPONSE[indexer_name])
    )

    results = await indexer.search("anything", use_cache=False)

    assert results is not None
    r = results[0]
    assert r.seeders == 0
    assert r.leechers == 0
    assert r.size == 0
    assert r.title == "unknown"
    assert r.source == "unknown"
    # a null magnet still falls back to the download link
    assert r.magnet_uri == "http://mock.indexer.url/dl/mock"

    # the S:L cell the results table builds must not read "None"
    assert f"{r.seeders!s}:{r.leechers!s}" == "0:0"


def _write_marker(path: str) -> list[Any]:
    with open(path, "w") as marker:
        marker.write("ran")
    return []


class _Planted:
    def __init__(self, path: str) -> None:
        self.path = path

    def __reduce__(self) -> tuple[Any, ...]:
        return (_write_marker, (self.path,))


@respx.mock
async def test_tampered_cache_entry_is_a_miss(
    indexer: BaseIndexer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    indexer_name = indexer.__class__.__name__.removesuffix("Indexer").lower()
    route = respx.get(indexer.get_search_url()).mock(
        Response(200, json=MOCK_SEARCH_RESPONSE[indexer_name])
    )
    marker = tmp_path / "marker"

    with Cache(tmp_path / "cache", disk=type(cache_module.cache.disk)) as cache:
        monkeypatch.setattr(f"torrra.indexers.{indexer_name}.cache", cache)
        await indexer.search("arch linux iso")
        with Cache(tmp_path / "cache", disk=Disk) as other_writer:
            key = cache.make_key(indexer_name, "arch linux iso")
            other_writer.set(key, _Planted(str(marker)))

        results = await indexer.search("arch linux iso")

    assert not marker.exists()
    assert route.call_count == 2
    assert results is not None
    assert results[0].title == "Arch Linux ISO (Mock)"
