import os
from pathlib import Path

from torrra.core.exceptions import DownloadPathError


def normalize_download_path(value: str | os.PathLike[str]) -> Path:
    """Normalize an absolute download directory path."""
    try:
        raw_value = os.fspath(value)
    except TypeError as exc:
        raise DownloadPathError("Download path must be a string.") from exc
    if not isinstance(raw_value, str):
        raise DownloadPathError("Download path must be a string.")

    raw_value = raw_value.strip()
    if not raw_value:
        raise DownloadPathError("Download path cannot be empty.")

    path = Path(raw_value)
    if not path.is_absolute():
        raise DownloadPathError(f"Download path must be absolute: {raw_value}")

    return Path(os.path.normpath(raw_value))


def prepare_download_path(
    value: str | os.PathLike[str], *, create: bool = True
) -> Path:
    """Return a usable download directory, optionally creating it."""
    path = normalize_download_path(value)

    try:
        if path.exists():
            if not path.is_dir():
                raise DownloadPathError(f"Download path is not a directory: {path}")
        elif create:
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise DownloadPathError(f"Download directory does not exist: {path}")
    except DownloadPathError:
        raise
    except (OSError, ValueError) as exc:
        raise DownloadPathError(
            f"Cannot create or access download directory '{path}': {exc}"
        ) from exc

    if not os.access(path, os.W_OK | os.X_OK):
        raise DownloadPathError(f"Download directory is not writable: {path}")

    return path
