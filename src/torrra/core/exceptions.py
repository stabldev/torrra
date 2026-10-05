class ConfigError(Exception):
    """Config error."""


class IndexerError(Exception):
    """Indexer error."""


class DownloadError(Exception):
    """Torrent download error."""


class DownloadPathError(DownloadError):
    """Invalid or inaccessible download path."""
