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
        return f"{int(size_bytes)}B"

    for unit in ["K", "M", "G", "T"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            number = (
                f"{size_bytes:.1f}".rstrip("0").rstrip(".")
                if size_bytes < 10
                else str(int(size_bytes))
            )
            return f"{number}{unit}"
    return f"{int(size_bytes)}P"


def human_readable_eta(seconds: float | None, is_seeding: bool = False) -> str:
    if is_seeding or seconds is None or seconds < 0 or seconds == float("inf"):
        return "∞"

    total_seconds = int(seconds)
    if total_seconds == 0:
        return "0s"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h" if hours > 0 else f"{days}d"
    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    if minutes > 0:
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    return f"{secs}s"


def lazy_import(dotted_path: str):
    import importlib

    try:
        module_path, obj_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, obj_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"failed to import: {dotted_path}\n{e}")
