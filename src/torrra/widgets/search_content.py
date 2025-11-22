from contextlib import suppress
from typing import cast

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, Static
from typing_extensions import override

from torrra._types import Indexer, Torrent
from torrra.core.torrent import TorrentManager
from torrra.indexers.base import BaseIndexer
from torrra.utils.helpers import human_readable_size, lazy_import
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.details_panel import DetailsPanel
from torrra.widgets.spinner import Spinner


class SearchContent(Vertical):
    COLS: list[tuple[str, str, int]] = [
        ("No", "no_col", 2),
        ("Title", "title_col", 25),
        ("Size", "size_col", 10),
        ("S:L", "seeders_leechers_col", 6),
    ]

    class SearchResults(Message):
        def __init__(self, results: list[Torrent], query: str) -> None:
            self.results: list[Torrent] = results
            self.query: str = query
            super().__init__()

    class DownloadRequested(Message):
        def __init__(self, torrent: Torrent) -> None:
            self.torrent: Torrent = torrent
            super().__init__()

    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__(id="search_content")
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

        # instance-level cache
        self._indexer_instance_cache: BaseIndexer | None = None

        # application states
        self._search_results_map: dict[str, Torrent] = {}
        self._selected_torrent: Torrent | None = None

        # ui refs (cached later)
        self._search_input: Input
        self._table: AutoResizingDataTable[str]
        self._details_panel: DetailsPanel
        self._loader: Vertical

    @override
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search...", value=self.search_query)
        yield AutoResizingDataTable(cursor_type="row", classes="hidden")
        yield DetailsPanel()
        with Vertical(id="loader"):
            yield Static()
            yield Spinner(name="shark")

    def on_mount(self) -> None:
        self._search_input = self.query_one(Input)
        self._search_input.border_title = "search"

        self._table = self.query_one(AutoResizingDataTable)
        self._table.expand_col = "title_col"
        self._table.border_title = "results"

        self._details_panel = self.query_one(DetailsPanel)
        self._details_panel.border_title = "details"

        self._loader = self.query_one("#loader", Vertical)
        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)
        # send initial search
        self.post_message(Input.Submitted(self._search_input, self.search_query))

    def key_s(self) -> None:
        self._search_input.focus()

    def key_r(self) -> None:
        self._table.focus()

    def key_d(self) -> None:
        if self._selected_torrent:
            tm = TorrentManager()
            tm.add_torrent(self._selected_torrent)
            self.post_message(self.DownloadRequested(self._selected_torrent))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        if not query:
            return

        self._table.add_class("hidden")
        self._table.clear()
        self._details_panel.add_class("hidden")
        self._loader.remove_class("hidden")
        cast(Spinner, self._loader.children[1]).resume()
        cast(Static, self._loader.children[0]).update(
            f"Searching for [b]{query}[/b]..."
        )

        self._perform_search(query)

    @work(exclusive=True)
    async def _perform_search(self, query: str) -> None:
        indexer = self._get_indexer_instance()
        results = []

        with suppress(Exception):
            results = await indexer.search(query, use_cache=self.use_cache)
        self.post_message(self.SearchResults(results, query))

    @on(SearchResults)
    def on_search_results(self, message: SearchResults) -> None:
        if not message.results:
            cast(Spinner, self._loader.children[1]).pause()
            cast(Static, self._loader.children[0]).update(
                f"Nothing Found for [b]{message.query}[/b]"
            )  # show loader and exit
            return

        self._loader.add_class("hidden")
        self._table.remove_class("hidden")
        self._table.focus()  # initial focus table
        self._table.border_title = (
            f"{self._table.border_title} ({len(message.results)})"
        )

        seen: set[str] = set()
        for idx, torrent in enumerate(message.results):
            if torrent.magnet_uri in seen:
                continue

            seen.add(torrent.magnet_uri)
            self._search_results_map[torrent.magnet_uri] = torrent
            self._table.add_row(
                str(idx + 1),
                torrent.title,
                human_readable_size(torrent.size),
                f"{str(torrent.seeders)}:{str(torrent.leechers)}",
                key=torrent.magnet_uri,
            )

    def on_details_panel_closed(self):
        self._selected_torrent = None
        self._table.focus()

    def on_data_table_row_selected(
        self, event: AutoResizingDataTable.RowSelected
    ) -> None:
        magnet_uri = cast(str, event.row_key.value)
        self._selected_torrent = self._search_results_map.get(magnet_uri)
        if not self._selected_torrent:
            return

        details = f"""
[b]{self._selected_torrent.title}[/b]
[b]Size:[/b] {human_readable_size(self._selected_torrent.size)} - [b]Seeders:[/b] {self._selected_torrent.seeders} - [b]Leechers:[/b] {self._selected_torrent.leechers} - [b]Source:[/b] {self._selected_torrent.source}

[dim]Press 'd' to download.[/dim]
"""

        self._details_panel.update(details.strip())
        self._details_panel.remove_class("hidden")
        self._details_panel.focus()

    def _get_indexer_instance(self) -> BaseIndexer:
        if self._indexer_instance_cache:
            return self._indexer_instance_cache

        name = self.indexer.name
        indexer_cls_str = f"torrra.indexers.{name}.{name.title()}Indexer"

        indexer_cls = lazy_import(indexer_cls_str)
        assert issubclass(indexer_cls, BaseIndexer)
        indexer_instance = indexer_cls(
            url=self.indexer.url, api_key=self.indexer.api_key
        )

        self._indexer_instance_cache = indexer_instance
        return indexer_instance
