DEFAULT_CACHE_TTL = 300  # 5 mins
DEFAULT_TIMEOUT = 10  # 10 sec
DEFAULT_MAX_RETRIES = 3
DEFAULT_SORT = "relevance"
# "auto" means each sort key uses its own natural direction, so title reads A-Z
# while seeders reads high-to-low. an explicit "asc"/"desc" overrides that.
DEFAULT_SORT_ORDER = "auto"
DEFAULT_MIN_SEEDERS = 0
# global (session-wide) bandwidth caps in bytes/sec; 0 = unlimited.
# toggled at runtime with the "t" keybind ("turtle mode").
DEFAULT_SPEED_LIMIT_UPLOAD = 0
DEFAULT_SPEED_LIMIT_DOWNLOAD = 0
