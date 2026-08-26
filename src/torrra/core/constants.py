DEFAULT_CACHE_TTL = 300  # 5 mins
DEFAULT_TIMEOUT = 10  # 10 sec
DEFAULT_MAX_RETRIES = 3
DEFAULT_SORT = "relevance"
# "auto" means each sort key uses its own natural direction, so title reads A-Z
# while seeders reads high-to-low. an explicit "asc"/"desc" overrides that.
DEFAULT_SORT_ORDER = "auto"
DEFAULT_MIN_SEEDERS = 0
# global (session-wide) bandwidth caps; defaults mirror qBittorrent's
# alternative-speed limits (10 KB/s in both directions). accepts human-readable
# units ("10 KB/s", "2M", "500K") or bare bytes/sec numbers; 0/unlimited = no cap.
DEFAULT_SPEED_LIMIT_UPLOAD = "10 KB/s"
DEFAULT_SPEED_LIMIT_DOWNLOAD = "10 KB/s"
DEFAULT_MAX_RATIO = 0.0
DEFAULT_MAX_SEED_TIME = 0
