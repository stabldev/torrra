import importlib

from torrra.indexers import INDEXERS


def get_indexer(name: str):
    indexer_module_path = INDEXERS[name]
    return importlib.import_module(indexer_module_path).Indexer()
