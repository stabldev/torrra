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


def lazy_import(dotted_path: str):
    import importlib

    try:
        module_path, obj_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, obj_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"failed to import: {dotted_path}\n{e}")
