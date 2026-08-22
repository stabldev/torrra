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
        "k": 1024,
        "kb": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
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
