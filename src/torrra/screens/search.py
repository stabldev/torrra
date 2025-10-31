import os
import tempfile
import time
from typing import Any, ClassVar, cast, override

import httpx
import libtorrent as lt
from textual import on, work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.types import CSSPathType
from textual.widgets import DataTable, Input, LoadingIndicator, ProgressBar, Static
from textual.widgets.data_table import ColumnKey

from torrra._types import Indexer, Torrent
from torrra.core.context import config
from torrra.indexers.jackett import JackettIndexer
from torrra.indexers.prowlarr import ProwlarrIndexer
from torrra.utils.fs import get_resource_path
from torrra.utils.helpers import human_readable_size


class SearchScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        ("l", "select_cursor", "Select item"),
        ("k", "cursor_up", "Go to previous row"),
        ("ctrl+u", "page_up", "Scroll up"),
        ("j", "cursor_down", "Go to next row"),
        ("ctrl+d", "page_down", "Scroll down"),
        ("g", "scroll_top", "Go to top"),
        ("G", "scroll_bottom", "Go to bottom"),
    ]

    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("screens/search.css")
    # https://github.com/edward-jazzhands/eds-sandbox/blob/main/python/textual/examples/datatable_expandcol.py
    no_col_width: int = 3
    title_col_minimum: int = 25  # dynamic
    size_col_width: int = 10
    seeders_col_width: int = 4
    leechers_col_width: int = 5
    source_col_width: int = 6
    other_cols_total: int = (
        no_col_width
        + size_col_width
        + seeders_col_width
        + leechers_col_width
        + source_col_width
    )

    class SearchResults(Message):
        def __init__(self, results: list[Torrent], query: str) -> None:
            self.results: list[Torrent] = results
            self.query: str = query
            super().__init__()

    def __init__(self, indexer: Indexer | None, initial_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer | None = indexer
        self.initial_query: str = initial_query
        self.use_cache: bool = use_cache
        # libtorrent
        self.lt_session: lt.session | None = None
        self.lt_handle: lt.torrent_handle | None = None
        self.lt_paused: bool = False

    @override
    def compose(self) -> ComposeResult:
        with Vertical():
            # search input
            search_input = Input(
                placeholder="Search...", id="search", value=self.initial_query
            )
            search_input.border_title = "[$secondary]s[/]earch"
            yield search_input
            # loading indicator
            with Vertical(id="loader"):
                yield Static(id="status")
                yield LoadingIndicator(id="indicator")
            # results data-table
            results_dt: DataTable[None] = DataTable(
                id="results_table",
                cursor_type="row",
                show_cursor=True,
                cell_padding=2,
                classes="hidden",
            )
            results_dt.border_title = "[$secondary]r[/]esults"
            yield results_dt
            # downloads container
            with Container(id="downloads_container") as c:
                c.border_title = "[$secondary]d[/]ownloads"
                c.can_focus = True
                yield Static("No active downloads", id="status")
                with Horizontal(id="progressbar-and-actions", classes="hidden"):
                    yield ProgressBar(total=100, id="progressbar")
                    yield Static(
                        "[$secondary-muted][$secondary]p[/$secondary]ause [$secondary]r[/$secondary]esume",
                        id="actions",
                    )

    def on_mount(self) -> None:
        self.post_message(
            Input.Submitted(self.query_one("#search", Input), self.initial_query)
        )

        table = cast(DataTable[None], self.query_one("#results_table", DataTable))
        table.add_column("No.", width=self.no_col_width, key="no_col")
        table.add_column("Title", width=self.title_col_minimum, key="title_col")
        table.add_column("Size", width=self.size_col_width, key="size_col")
        table.add_column("Seed", width=self.seeders_col_width, key="seeders_col")
        table.add_column("Leech", width=self.leechers_col_width, key="leechers_col")
        table.add_column("Source", width=self.source_col_width, key="source_col")

    def on_unmount(self) -> None:
        # clean libtorrent session
        if self.lt_session and self.lt_handle:
            self.lt_session.remove_torrent(self.lt_handle)

    def on_resize(self) -> None:
        table = cast(DataTable[None], self.query_one("#results_table", DataTable))

        total_cell_padding = table.cell_padding * 2 * len(table.columns)
        # space taken for border and padding
        border_and_padding = 4
        available_width = (
            self.size.width
            - self.other_cols_total
            - total_cell_padding
            - border_and_padding
        )

        second_col_width = max(self.title_col_minimum, available_width)
        table.columns[ColumnKey("title_col")].width = second_col_width

    def key_s(self) -> None:
        self.query_one("#search", Input).focus()

    def key_p(self) -> None:
        downloads_container = self.query_one("#downloads_container", Container)
        if not downloads_container.has_focus or not self.lt_handle or self.lt_paused:
            return

        self.lt_handle.pause()
        self.lt_paused = True

    def key_r(self) -> None:
        downloads_container = self.query_one("#downloads_container", Container)
        if (
            not downloads_container.has_focus
            or not self.lt_handle
            or not self.lt_paused
        ):
            return

        self.lt_handle.resume()
        self.lt_paused = False

    # Vim bindings
    def action_cursor_up(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_cursor_up()

    def action_cursor_down(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_cursor_down()

    def action_scroll_top(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_scroll_top()

    def action_scroll_bottom(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_scroll_bottom()

    def action_select_cursor(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_select_cursor()

    def action_page_down(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_page_down()

    def action_page_up(self) -> None:
        table = self.query_one("#results_table", DataTable)
        table.action_page_up()

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        query = event.value
        if not query:
            return

        table = cast(DataTable[None], self.query_one("#results_table", DataTable))
        loader = self.query_one("#loader", Vertical)
        loader_text = self.query_one("#loader #status", Static)

        table.add_class("hidden")
        table.clear()
        loader.remove_class("hidden")
        loader_text.update(f'Searching for: "[b]{query}[/]"')

        self._perform_search(query)

    @on(DataTable.RowSelected, "#results_table")
    def handle_select(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        magnet_uri = row_key.value

        self.query_one("#progressbar-and-actions", Horizontal).remove_class("hidden")
        self.query_one("#search", Input).disabled = True
        cast(DataTable[None], event.control).disabled = True
        self._update_download_ui("[b $success]Fetching Metadata...[/]", 0)
        self._download_torrent(magnet_uri)

    @work(exclusive=True, thread=True)
    async def _perform_search(self, query: str) -> None:
        indexer = self._get_indexer_instance()
        results = []
        if indexer:
            try:
                results = await indexer.search(query, use_cache=self.use_cache)
            except Exception as e:
                self.log.error(f"error during search: {e}")

        self.post_message(self.SearchResults(results, query))

    @on(SearchResults)
    def _show_search_results(self, message: SearchResults) -> None:
        table = cast(DataTable[str], self.query_one("#results_table", DataTable))
        loader = self.query_one("#loader", Vertical)
        loader_text = loader.query_one(Static)

        if not message.results:
            loader_text.update(f'Nothing found for "[b]{message.query}[/b]"')
            return

        loader.add_class("hidden")
        table.remove_class("hidden")

        seen_magnets: set[str] = set()
        for idx, torrent in enumerate(message.results):
            if torrent.magnet_uri is None:
                continue
            if torrent.magnet_uri in seen_magnets:
                continue

            seen_magnets.add(torrent.magnet_uri)

            table.add_row(
                str(idx + 1),
                torrent.title,
                human_readable_size(torrent.size),
                str(torrent.seeders),
                str(torrent.leechers),
                torrent.source,
                key=torrent.magnet_uri,
            )

        table.focus()

    @work(exclusive=True, thread=True)
    async def _download_torrent(self, magnet_uri: str) -> None:
        resolved = await self._resolve_magnet_uri_or_torrent_info(magnet_uri)
        if resolved is None:
            # TODO: show notify (requuires custom styling)
            return

        self.lt_session = lt.session()
        self.lt_session.listen_on(6881, 6891)

        params: dict[str, Any] = {
            "save_path": config.get("general.download_path"),
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,
        }

        if isinstance(resolved, str) and resolved.startswith("magnet:"):
            self.lt_handle = lt.add_magnet_uri(self.lt_session, resolved, params)
        else:
            params["ti"] = resolved
            self.lt_handle = self.lt_session.add_torrent(params)

        while not self.lt_handle.has_metadata():
            time.sleep(0.5)

        torrent_info = self.lt_handle.get_torrent_info()
        title = torrent_info.name()
        total_size = human_readable_size(torrent_info.total_size())

        status_text_template = (
            f"[b $secondary]Title: [$primary]{title}[/$primary] - "
            "Mode: [$success]{status}[/$success] - "
            "Seeds: {seeds} - "
            "Peers: {peers} - "
        )

        while not self.lt_handle.is_seed():
            s = self.lt_handle.status()
            seed_status = (
                status_text_template.format(
                    status="Paused" if self.lt_paused else "Download",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Size: {total_size}[/]"
            )

            self.app.call_from_thread(
                self._update_download_ui,
                seed_status,
                s.progress * 100,
            )

            time.sleep(1)

        while True:
            s = self.lt_handle.status()
            seed_status = (
                status_text_template.format(
                    status="Paused" if self.lt_paused else "Seed",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Uploaded: {human_readable_size(s.total_upload)}[/]"
            )

            self.app.call_from_thread(self._update_download_ui, seed_status, 100)
            time.sleep(5)

    def _update_download_ui(self, status: str, progress: float) -> None:
        self.query_one("#downloads_container #status", Static).update(status)
        self.query_one("#downloads_container #progressbar", ProgressBar).update(
            progress=progress
        )

    def _get_indexer_instance(self) -> JackettIndexer | ProwlarrIndexer | None:
        if not self.indexer:
            return

        INDEXER_MAP = {"jackett": JackettIndexer, "prowlarr": ProwlarrIndexer}

        indexer = INDEXER_MAP[self.indexer.name]
        return indexer(url=self.indexer.url, api_key=self.indexer.api_key)

    async def _resolve_magnet_uri_or_torrent_info(
        self, input_uri: str
    ) -> str | lt.torrent_info | None:
        if input_uri.startswith("magnet:"):
            return input_uri

        try:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                resp = await client.get(input_uri)
                if resp.status_code in (301, 302):
                    return resp.headers.get("location")

                content_type = resp.headers.get("content-type")
                if "application/x-bittorrent" in content_type or input_uri.endswith(
                    ".torrent"
                ):
                    with tempfile.NamedTemporaryFile(
                        suffix=".torrent", delete=False
                    ) as tmp_file:
                        tmp_file.write(resp.content)
                        tmp_path = tmp_file.name

                    try:
                        return lt.torrent_info(tmp_path)
                    finally:
                        # cleanup the tmp torrent file
                        os.remove(tmp_path)
                return None

        except Exception as e:
            self.log.error(f"an unexpected error occurred: {e}")
            return None
