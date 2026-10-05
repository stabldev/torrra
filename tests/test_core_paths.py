from pathlib import Path
from typing import Any, cast

import pytest

from torrra.core.exceptions import DownloadPathError
from torrra.core.paths import normalize_download_path, prepare_download_path


def test_normalize_download_path_collapses_parent_segments(tmp_path: Path):
    path = tmp_path / "media" / ".." / "downloads"

    assert normalize_download_path(path) == tmp_path / "downloads"


@pytest.mark.parametrize("value", ["", "relative/path"])
def test_normalize_download_path_rejects_invalid_values(value: str):
    with pytest.raises(DownloadPathError):
        normalize_download_path(value)


def test_normalize_download_path_rejects_non_path_value():
    with pytest.raises(DownloadPathError, match="must be a string"):
        normalize_download_path(cast(Any, object()))


def test_prepare_download_path_creates_missing_directory(tmp_path: Path):
    destination = tmp_path / "nested" / "downloads"

    assert prepare_download_path(destination) == destination
    assert destination.is_dir()


def test_prepare_download_path_does_not_create_restore_destination(tmp_path: Path):
    destination = tmp_path / "unmounted-drive"

    with pytest.raises(DownloadPathError, match="does not exist"):
        prepare_download_path(destination, create=False)

    assert not destination.exists()


def test_prepare_download_path_rejects_file(tmp_path: Path):
    destination = tmp_path / "not-a-directory"
    destination.write_text("data")

    with pytest.raises(DownloadPathError, match="not a directory"):
        prepare_download_path(destination)


def test_prepare_download_path_rejects_unwritable_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("torrra.core.paths.os.access", lambda *_args: False)

    with pytest.raises(DownloadPathError, match="not writable"):
        prepare_download_path(tmp_path)


def test_prepare_download_path_wraps_invalid_filesystem_path(tmp_path: Path):
    with pytest.raises(DownloadPathError, match="Cannot create or access"):
        prepare_download_path(str(tmp_path / "invalid\0path"))
