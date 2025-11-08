from functools import lru_cache

from torrra._types import Indexer
from torrra.indexers.jackett import JackettIndexer
from torrra.indexers.prowlarr import ProwlarrIndexer


@lru_cache
def get_indexer(indexer: Indexer):
    mapping = {"jackett": JackettIndexer, "prowlarr": ProwlarrIndexer}
    cls = mapping[indexer.name]

    return cls(url=indexer.url, api_key=indexer.api_key)
