import json
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from torrra._types import Torrent, TorrentDict


class HistoryManager:
    def __init__(self) -> None:
        self._history_file: Path = Path(user_data_dir("torrra")) / "history.json"
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._history_file.exists():
            self._history_file.touch()
            self._history_file.write_text("[]")

    def add_torrent(self, torrent: Torrent) -> None:
        history = self._load_history()
        if torrent.magnet_uri and any(
            t.get("magnet_uri") == torrent.magnet_uri for t in history
        ):
            return

        history.append(torrent.to_dict())
        self._save_history(history)

    def get_all_torrents(self) -> list[Torrent]:
        history = self._load_history()
        return [Torrent.from_dict(TorrentDict(**t)) for t in history]

    def _load_history(self) -> list[dict[str, Any]]:
        try:
            with open(self._history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_history(self, data: list[dict[str, Any]]) -> None:
        with open(self._history_file, "w") as f:
            json.dump(data, f, indent=2)
