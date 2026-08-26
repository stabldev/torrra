from itertools import pairwise


def human_readable_size(size_bytes: float, short: bool = False) -> str:
    if not short:
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    # short version
    if size_bytes < 1024:
        return f"{int(size_bytes)} B"

    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            number = (
                f"{size_bytes:.1f}".rstrip("0").rstrip(".")
                if size_bytes < 10
                else str(int(size_bytes))
            )
            return f"{number} {unit}"
    size_bytes /= 1024.0
    return f"{int(size_bytes)} PB"


def human_readable_eta(seconds: float | None, is_seeding: bool = False) -> str:
    if is_seeding or seconds is None or seconds < 0 or seconds == float("inf"):
        return "∞"

    total_seconds = int(seconds)
    if total_seconds == 0:
        return "0s"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    units = [(days, "d"), (hours, "h"), (minutes, "m"), (secs, "s")]
    for (val, unit), (sub_val, sub_unit) in pairwise(units):
        if val > 0:
            return f"{val}{unit} {sub_val}{sub_unit}" if sub_val > 0 else f"{val}{unit}"
    return f"{secs}s"


def parse_speed_limit(text: str) -> int:
    """Parse a human speed limit into bytes/second.

    Returns ``-1`` for unlimited (empty, ``0``, ``unlimited`` or ``off``).
    Accepts suffixes ``K``/``KB`` (1024), ``M``/``MB`` (1024**2) and
    ``G``/``GB`` (1024**3), optionally followed by ``/s``. Raises
    ``ValueError`` on invalid input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned.endswith("/s"):
        cleaned = cleaned[:-2].strip()
    if cleaned in ("", "0", "unlimited", "off", "none"):
        return -1

    units = {
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "mib": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "gib": 1024**3,
    }

    for suffix, multiplier in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if cleaned.endswith(suffix):
            number_part = cleaned[: -len(suffix)].strip()
            value = float(number_part) * multiplier
            if value < 0:
                raise ValueError("speed limit must not be negative")
            return int(value)

    # bare number => bytes/second
    value = float(cleaned)
    if value < 0:
        raise ValueError("speed limit must not be negative")
    return int(value)


def coerce_speed_limit(value: object) -> int:
    """Coerce a stored speed-limit config value to bytes/second.

    Ints pass through (normalized to >= 0); strings (e.g. ``"10 KB/s"``, ``"2M"``
    in config.toml) are parsed, and anything unparsable or unlimited (``"0"``,
    ``"unlimited"``) falls back to ``0`` instead of crashing readers.
    """
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, parse_speed_limit(str(value)))
    except ValueError:
        return 0


def parse_ratio_limit(text: str) -> float:
    """Parse a seed ratio limit into a float.

    Returns ``-1.0`` for unlimited (empty, ``0``, ``0.0``, ``unlimited``, ``off``, or ``none``).
    Raises ``ValueError`` on invalid or negative input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned in ("", "0", "0.0", "unlimited", "off", "none"):
        return -1.0
    try:
        val = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"invalid ratio limit: '{text}'") from exc
    if val < 0:
        raise ValueError("ratio limit must not be negative")
    if val == 0:
        return -1.0
    return val


def format_ratio_limit(value: float | None) -> str:
    """Format a ratio limit for prefilling input forms."""
    if value is None or value <= 0:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def coerce_ratio_limit(value: object) -> float:
    """Coerce a ratio limit config or db value to float >= 0.0."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    try:
        parsed = parse_ratio_limit(str(value))
        return max(0.0, parsed)
    except ValueError:
        return 0.0


def parse_seeding_time(text: str) -> int:
    """Parse a seeding duration limit into minutes.

    Returns ``-1`` for unlimited (empty, ``0``, ``unlimited``, ``off``, or ``none``).
    Accepts suffixes ``d``/``day``/``days``, ``h``/``hr``/``hrs``/``hours``,
    ``m``/``min``/``mins``/``minutes``, or bare minutes.
    Raises ``ValueError`` on invalid or negative input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned in ("", "0", "unlimited", "off", "none"):
        return -1

    units = [
        (("days", "day", "d"), 1440),
        (("hours", "hour", "hrs", "hr", "h"), 60),
        (("minutes", "minute", "mins", "min", "m"), 1),
    ]

    for suffixes, multiplier in units:
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                number_part = cleaned[: -len(suffix)].strip()
                try:
                    val = float(number_part) * multiplier
                except ValueError as exc:
                    raise ValueError(f"invalid seeding time: '{text}'") from exc
                if val < 0:
                    raise ValueError("seeding time must not be negative")
                return int(val)

    try:
        val = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"invalid seeding time: '{text}'") from exc
    if val < 0:
        raise ValueError("seeding time must not be negative")
    return int(val)


def format_seeding_time(minutes: int | None) -> str:
    """Format seeding duration in minutes for prefilling input forms."""
    if minutes is None or minutes <= 0:
        return ""
    if minutes % 1440 == 0:
        return f"{minutes // 1440}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def coerce_seeding_time(value: object) -> int:
    """Coerce a seeding time config or db value to integer minutes >= 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    try:
        parsed = parse_seeding_time(str(value))
        return max(0, parsed)
    except ValueError:
        return 0


def lazy_import(dotted_path: str):
    import importlib

    try:
        module_path, obj_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, obj_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"failed to import: {dotted_path}\n{e}")


def get_tomllib():
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # Python <3.11
        import tomli as tomllib  # type: ignore

    return tomllib
