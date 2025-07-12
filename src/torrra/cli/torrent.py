import importlib
from typing import List

import questionary
from prompt_toolkit.shortcuts import CompleteStyle
from questionary import Choice
from rich.console import Console

from torrra.constants import UI_STRINGS
from torrra.core.downloader import download_magnet
from torrra.indexers import INDEXERS_MAP
from torrra.types import Torrent
from torrra.utils import styles, welcome

console = Console()


def run_torrent_flow() -> None:
    welcome.show_welcome()

    query = questionary.text(UI_STRINGS["prompt_search_query"], style=styles.TEXT).ask()
    if not query:
        return

    indexer_name = questionary.select(
        UI_STRINGS["prompt_choose_indexer"],
        choices=list(INDEXERS_MAP.keys()),
        style=styles.SELECT,
    ).ask()
    if not indexer_name:
        return

    indexer_module_path = INDEXERS_MAP[indexer_name]
    indexer = importlib.import_module(indexer_module_path).Indexer()

    with console.status(
        UI_STRINGS["status_searching"].format(indexer=indexer_name, query=query)
    ):
        torrents: List[Torrent] = indexer.search(query)

    if not torrents:
        console.print(UI_STRINGS["error_no_results"])
        return

    torrent_choices = [
        Choice(title=torrent.title, value=torrent) for torrent in torrents
    ]

    selected_torrent: Torrent | None = questionary.select(
        UI_STRINGS["prompt_select_result"],
        choices=torrent_choices,
        style=styles.SELECT,
    ).ask()
    if not selected_torrent:
        return

    save_path = questionary.path(
        UI_STRINGS["prompt_download_path"],
        only_directories=True,
        complete_style=CompleteStyle.COLUMN,
        style=styles.TEXT,
    ).ask()
    if not save_path:
        return

    # TODO: handle config
    download_magnet(selected_torrent.magnet_uri, save_path)
