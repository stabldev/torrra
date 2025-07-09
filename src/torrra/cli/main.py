import questionary

from prompt_toolkit.shortcuts import CompleteStyle
from questionary import Choice
from typing import List
from rich.console import Console

from torrra.constants import UI_STRINGS
from torrra.downloader import download_magnet
from torrra.indexers import INDEXERS
from torrra.types import Torrent
from torrra.utils import get_indexer

console = Console()


def main() -> None:
    query = questionary.text(UI_STRINGS["prompt_search_query"]).ask()
    if not query:
        return

    indexer_name = questionary.select(
        UI_STRINGS["prompt_choose_indexer"], choices=list(INDEXERS.keys())
    ).ask()
    indexer = get_indexer(indexer_name)

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
        UI_STRINGS["prompt_select_result"], choices=torrent_choices
    ).ask()
    if not selected_torrent:
        return

    save_path = questionary.path(
        UI_STRINGS["prompt_download_path"],
        only_directories=True,
        complete_style=CompleteStyle.COLUMN,
    ).ask()

    # initiate download
    download_magnet(selected_torrent.magnet_uri, save_path)
