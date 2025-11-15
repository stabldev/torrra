from httpx import Response
import pytest
import respx

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
