from __future__ import annotations

from typing import Any, ClassVar, cast

import httpx
import libtorrent as lt
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, Static
from typing_extensions import override

from torrra._types import DownloadSelection, Indexer, Torrent
from torrra.core.config import get_config
from torrra.core.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_SEEDERS,
    DEFAULT_SORT,
    DEFAULT_SORT_ORDER,
    DEFAULT_TIMEOUT,
)
from torrra.core.download import get_download_manager
from torrra.core.exceptions import ConfigError, DownloadError, IndexerError
from torrra.core.results import (
    ResultView,
    SortKey,
    parse_min_seeders,
    parse_sort_key,
    parse_sort_order,
)
from torrra.core.torrent import get_torrent_manager
from torrra.indexers.base import BaseIndexer
from torrra.screens.file_selection import FileSelectionScreen
from torrra.screens.sort_selector import SortSelectorScreen
from torrra.utils.helpers import human_readable_size, lazy_import
from torrra.utils.magnet import resolve_torrent
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.details_panel import DetailsPanel
from torrra.widgets.search_input import SearchInput
from torrra.widgets.spinner import Spinner


class SearchContent(Vertical):
    COLS: ClassVar[list[tuple[str, str, int]]] = [
        ("No", "no_col", 2),
        ("Title", "title_col", 25),
        ("Size", "size_col", 10),
        ("S:L", "seeders_leechers_col", 6),
    ]

    # clicking a column header sorts by it; "No" restores the indexer's order
    COL_SORTS: ClassVar[dict[str, SortKey]] = {
        "no_col": SortKey.RELEVANCE,
        "title_col": SortKey.TITLE,
        "size_col": SortKey.SIZE,
        "seeders_leechers_col": SortKey.SEEDERS,
    }

    # these only fire while the results table has focus; the search Input
    # consumes printable keys before they can reach these bindings
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("s", "open_sort_menu"),
        Binding("S", "toggle_sort_order"),
        Binding("f", "toggle_seeded_only"),
        Binding("x", "clear_filters"),
    ]

    HINTS = "s sort · S order · f seeded · x reset"

    class DownloadRequested(Message):
        def __init__(self, torrent: Torrent) -> None:
            self.torrent: Torrent = torrent
            super().__init__()

    class SearchResults(Message):
        def __init__(self, results: list[Torrent], query: str) -> None:
            self.results: list[Torrent] = results
            self.query: str = query
            super().__init__()

    def __init__(
        self,
        indexer: Indexer,
        search_query: str,
        use_cache: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, id="search_content", **kwargs)
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache
        self._indexer_instance_cache: BaseIndexer | None = None

        # application states
        self._search_results_map: dict[str, Torrent] = {}
        self._selected_torrent: Torrent | None = None
        self._current_torrent_info: lt.torrent_info | None = None
        # ordering/filtering survives across searches in a session
        self._view: ResultView = self._build_view()

        # ui refs (cached later)
        self._search_input: Input
        self._table: AutoResizingDataTable[str]
        self._details_panel: DetailsPanel
        self._loader: Vertical

    @staticmethod
    def _config_defaults() -> tuple[SortKey, bool | None, int]:
        """Read the configured baseline: sort key, direction, and seeder floor.

        Shared by startup and `x` so the two can't drift apart.
        """
        config = get_config()

        sort_key = parse_sort_key(config.get("general.default_sort", DEFAULT_SORT))
        # a direction is meaningless for relevance, and honouring a configured
        # "desc" there would silently reverse the indexer's own ranking
        descending = (
            None
            if sort_key is SortKey.RELEVANCE
            else parse_sort_order(
                config.get("general.default_sort_order", DEFAULT_SORT_ORDER)
            )
        )
        min_seeders = parse_min_seeders(
            config.get("general.min_seeders", DEFAULT_MIN_SEEDERS), DEFAULT_MIN_SEEDERS
        )
        return sort_key, descending, min_seeders

    @classmethod
    def _build_view(cls) -> ResultView:
        sort_key, descending, min_seeders = cls._config_defaults()

        view = ResultView()
        view.set_sort(sort_key, descending)
        view.filters.min_seeders = min_seeders
        return view

    @override
    def compose(self) -> ComposeResult:
        yield SearchInput(placeholder="Search...", value=self.search_query)
        yield AutoResizingDataTable(cursor_type="row", classes="hidden")
        yield DetailsPanel()
        with Vertical(id="loader"):
            yield Static()
            yield Spinner(name="material")

    def on_mount(self) -> None:
        self._search_input = self.query_one(Input)
        self._search_input.border_title = "search"
        self._search_input.focus()

        self._table = self.query_one(AutoResizingDataTable)
        self._table.expand_col = "title_col"
        self._table.border_title = "results"

        self._details_panel = self.query_one(DetailsPanel)

        self._loader = self.query_one("#loader", Vertical)
        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)
        # send initial search
        self.post_message(Input.Submitted(self._search_input, self.search_query))

    async def on_data_table_row_selected(
        self, event: AutoResizingDataTable.RowSelected
    ) -> None:
        if getattr(self, "_is_selecting_files", False):
            return
        self._is_selecting_files = True

        magnet_uri = cast(str, event.row_key.value)
        self._selected_torrent = self._search_results_map.get(magnet_uri)
        if not self._selected_torrent:
            self._is_selecting_files = False
            return

        raw_magnet_uri = self._selected_torrent.magnet_uri
        resolved_magnet_uri, torrent_info = await resolve_torrent(raw_magnet_uri)

        if resolved_magnet_uri is None:
            self._is_selecting_files = False
            self.notify("Failed to resolve torrent URI", severity="error")
            return

        # update with resolved magnet_uri
        self._selected_torrent.magnet_uri = resolved_magnet_uri
        self._current_torrent_info = torrent_info

        config = get_config()
        if config.get("general.download_in_external_client", False):
            self._is_selecting_files = False
            self.app.open_url(resolved_magnet_uri)
            self.notify(
                "Opened in default magnet: handler",
                title="Torrent Opened",
            )
        else:  # continue with libtorrent file selection
            self.app.push_screen(
                FileSelectionScreen(
                    torrent=self._selected_torrent,
                    torrent_info=torrent_info,
                ),
                self._on_file_selection_done,
            )

    def _on_file_selection_done(self, selection: DownloadSelection | None) -> None:
        self._is_selecting_files = False
        if selection is None or not self._selected_torrent:
            return

        tm = get_torrent_manager()
        dm = get_download_manager()

        if tm.get_torrent(self._selected_torrent.magnet_uri):
            self.notify(
                "This torrent is already in your downloads.",
                title="Torrent Already Added",
                severity="warning",
            )
            return

        self._selected_torrent.file_priorities = selection.file_priorities
        self._selected_torrent.save_path = selection.save_path
        try:
            dm.add_torrent(
                self._selected_torrent.magnet_uri,
                is_paused=False,
                file_priorities=selection.file_priorities,
                torrent_info=getattr(self, "_current_torrent_info", None),
                save_path=selection.save_path,
            )
        except DownloadError as exc:
            self.notify(str(exc), title="Download Failed", severity="error")
            return

        tm.add_torrent(
            self._selected_torrent,
            file_priorities=selection.file_priorities,
            save_path=selection.save_path,
        )

        self.post_message(self.DownloadRequested(self._selected_torrent))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        if not query or not query.strip():
            self._table.add_class("hidden")
            self._table.clear()
            self._view.set_results([])
            self._search_results_map.clear()
            self._selected_torrent = None
            self._loader.remove_class("hidden")
            cast(Spinner, self._loader.children[1]).pause()
            cast(Static, self._loader.children[0]).update("Search for torrents...")
            return

        self._table.add_class("hidden")
        self._table.clear()
        # drop the previous result set so stale rows can't be re-rendered
        # by a sort/filter keypress while the new search is in flight
        self._view.set_results([])
        self._search_results_map.clear()
        self._selected_torrent = None
        self._loader.remove_class("hidden")
        cast(Spinner, self._loader.children[1]).resume()
        cast(Static, self._loader.children[0]).update(
            f"Searching for [b]{query}[/b]..."
        )

        self._perform_search(query)

    @work(exclusive=True)
    async def _perform_search(self, query: str) -> None:
        try:
            indexer = self._get_indexer_instance()
            results = await indexer.search(query, use_cache=self.use_cache)
            self.post_message(self.SearchResults(results or [], query))
        except (
            IndexerError,
            ConfigError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            RuntimeError,
        ):
            self.notify(
                "Search failed, check indexer settings",
                title="Search Failed",
                severity="error",
            )  # post empty results just to stop spinners
            self.post_message(self.SearchResults([], query))

    @on(SearchResults)
    def on_search_results(self, message: SearchResults) -> None:
        if not message.results:
            cast(Spinner, self._loader.children[1]).pause()
            cast(Static, self._loader.children[0]).update(
                f"Nothing Found for [b]{message.query}[/b]"
            )  # show loader and exit
            return

        self._view.set_results(message.results)

        self._loader.add_class("hidden")
        self._table.remove_class("hidden")
        self._table.focus()  # initial focus table
        self._render_rows()

    def _render_rows(self) -> None:
        """Single path from the view model to the table.

        Every state change - new search, sort, filter - funnels through here so
        row numbering and the lookup map can never drift out of sync.
        """
        rows = self._view.visible()

        self._table.clear()
        self._search_results_map.clear()

        for idx, torrent in enumerate(rows, start=1):
            self._search_results_map[torrent.magnet_uri] = torrent
            self._table.add_row(
                str(idx),
                torrent.title,
                human_readable_size(torrent.size),
                f"{torrent.seeders!s}:{torrent.leechers!s}",
                key=torrent.magnet_uri,
            )

        shown, total = len(rows), self._view.total
        count = f"{shown}/{total}" if shown != total else str(total)
        self._table.border_title = f"results ({count}) · {self._view.sort_label}"
        self._table.border_subtitle = self.HINTS
        # row numbers and swarm counts both outgrow the widths their columns
        # are declared with once a search returns a few hundred results
        self._table.fit_columns()

    def _refresh_view(self) -> None:
        """Re-render after a sort/filter change, unless nothing is loaded yet."""
        if not self._view.total:
            return

        self._selected_torrent = None
        self._render_rows()
        self._table.focus()

    def action_open_sort_menu(self) -> None:
        if not self._view.total:
            return
        self.app.push_screen(
            SortSelectorScreen(self._view.sort_key), self._apply_sort_choice
        )

    def _apply_sort_choice(self, key: SortKey | None) -> None:
        if key is None:  # cancelled
            return
        self._view.set_sort(key)
        self._refresh_view()

    def action_toggle_sort_order(self) -> None:
        self._view.toggle_direction()
        self._refresh_view()

    def action_toggle_seeded_only(self) -> None:
        filters = self._view.filters
        filters.min_seeders = 0 if filters.min_seeders else 1
        self._refresh_view()

    def action_clear_filters(self) -> None:
        # back to the configured baseline rather than hardcoded relevance, so a
        # configured default_sort stays reachable instead of being startup-only
        sort_key, descending, min_seeders = self._config_defaults()
        self._view.reset_to(sort_key, descending, min_seeders)
        self._refresh_view()

    @on(AutoResizingDataTable.HeaderSelected)
    def on_header_selected(self, event: AutoResizingDataTable.HeaderSelected) -> None:
        """Sort by clicking a column header, toggling on repeated clicks."""
        key = self.COL_SORTS.get(str(event.column_key.value))
        if key is None or not self._view.total:
            return

        # clicking the active column flips it; a new column starts in its
        # own natural direction. relevance has no direction to flip.
        if key is self._view.sort_key and key is not SortKey.RELEVANCE:
            self._view.toggle_direction()
        else:
            self._view.set_sort(key)

        self._refresh_view()

    def _get_indexer_instance(self) -> BaseIndexer:
        if self._indexer_instance_cache:
            return self._indexer_instance_cache

        name = self.indexer.name
        indexer_cls_str = f"torrra.indexers.{name}.{name.title()}Indexer"

        indexer_cls = lazy_import(indexer_cls_str)
        assert issubclass(indexer_cls, BaseIndexer)
        indexer_instance = indexer_cls(
            url=self.indexer.url,
            api_key=self.indexer.api_key,
            timeout=get_config().get("general.timeout", DEFAULT_TIMEOUT),
            max_retries=get_config().get("general.max_retries", DEFAULT_MAX_RETRIES),
        )

        self._indexer_instance_cache = indexer_instance
        return indexer_instance
