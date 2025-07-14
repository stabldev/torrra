from torrra.indexers import magnetdl, movierulz, yts

INDEXERS_MAP = {
    "yts": yts.Indexer,
    "magnetdl": magnetdl.Indexer,
    "movierulz": movierulz.Indexer,
}
