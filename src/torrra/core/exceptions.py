class ConfigError(Exception):
    """Custom error for config key issues."""

    pass


class JackettConnectionError(Exception):
    """Raised when Jackett is unreachable or misconfigured."""

    pass


class ProwlarrConnectionError(Exception):
    """Raised when Prowlarr is unreachable or misconfigured."""

    pass
