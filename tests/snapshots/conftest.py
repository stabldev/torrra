import pytest

from torrra._types import SessionStats
from torrra.core.download import DownloadManager


@pytest.fixture(autouse=True)
def mock_session_stats(monkeypatch: pytest.MonkeyPatch):
    """Ensure deterministic session stats in snapshot tests to prevent DHT flakes."""
    monkeypatch.setattr(
        DownloadManager,
        "get_session_stats",
        lambda self: SessionStats(
            download_rate=0.0,
            upload_rate=0.0,
            dht_nodes=0,
        ),
    )
