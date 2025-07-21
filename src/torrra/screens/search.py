import time
from typing import List, Optional

import libtorrent as lt
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Input, LoadingIndicator, ProgressBar, Static
from textual.widgets.data_table import ColumnKey

from torrra._types import Provider, Torrent
from torrra.core.context import config
from torrra.providers.jackett import JackettClient
from torrra.utils.fs import get_resource_path
from torrra.utils.helpers import human_readable_size


class SearchScreen(Screen):
    CSS_PATH = get_resource_path("screens/search.css")
    # https://github.com/edward-jazzhands/eds-sandbox/blob/main/python/textual/examples/datatable_expandcol.py
    no_col_width = 3
    title_col_minimum = 25  # dynamic
    size_col_width = 10
    seeders_col_width = 4
    leechers_col_width = 5
    source_col_width = 6
    other_cols_total = (
        no_col_width
        + size_col_width
        + seeders_col_width
        + leechers_col_width
        + source_col_width
    )

    class SearchResults(Message):
        def __init__(self, results: List[Torrent], query: str) -> None:
            self.results = results
            self.query = query
            super().__init__()

    def __init__(self, provider: Optional[Provider], initial_query: str):
        super().__init__()
        self.provider = provider
        self.initial_query = initial_query
        # libtorrent
        self.lt_session = None
        self.lt_handle = None
        self.lt_paused = False

    def compose(self) -> ComposeResult:
        search_input = Input(
            placeholder="Search...", id="search", value=self.initial_query
        )
        search_input.border_title = "[$secondary]s[/]earch"
        results_table = DataTable(
            id="results_table",
            cursor_type="row",
            show_cursor=True,
            cell_padding=2,
            classes="hidden",
        )
        results_table.border_title = "[$secondary]r[/]esults"

        with Vertical():
            yield search_input
            with Vertical(id="loader"):
                yield Static()
                yield LoadingIndicator()
            yield results_table
            with Container(id="downloads_container") as c:
                c.border_title = "[$secondary]d[/]ownloads"
                c.can_focus = True
                yield Static("No active downloads")
                with Horizontal(id="bar-and-actions", classes="hidden"):
                    yield ProgressBar(total=100)
                    yield Static(
                        "[$secondary-muted][$secondary]p[/$secondary]ause [$secondary]r[/$secondary]esume",
                        id="actions",
                        disabled=True,
                    )

    def on_mount(self) -> None:
        self.post_message(
            Input.Submitted(self.query_one("#search", Input), self.initial_query)
        )

        table = self.query_one("#results_table", DataTable)
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
        table = self.query_one("#results_table", DataTable)

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

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        query = event.value
        if not query:
            return

        table = self.query_one("#results_table", DataTable)
        loader = self.query_one("#loader", Vertical)
        loader_text = self.query_one("#loader Static", Static)

        table.add_class("hidden")
        table.clear()
        loader.remove_class("hidden")
        loader_text.update(f'Searching for: "[b]{query}[/]"')

        self._perform_search(query)

    @on(DataTable.RowSelected, "#results_table")
    def handle_select(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        magnet_uri = row_key.value

        self.query_one("#bar-and-actions", Horizontal).remove_class("hidden")
        self.query_one("#search", Input).disabled = True
        event.control.disabled = True
        self._download_torrent(magnet_uri)

    @work(exclusive=True, thread=True)
    async def _perform_search(self, query: str) -> None:
        client = self._get_client()
        results = []
        if client:
            try:
                results = await client.search(query)
            except Exception as e:
                self.log.error(f"error during search: {e}")

        self.post_message(self.SearchResults(results, query))

    @on(SearchResults)
    def _show_search_results(self, message: SearchResults) -> None:
        table = self.query_one("#results_table", DataTable)
        loader = self.query_one("#loader", Vertical)
        loader_text = loader.query_one(Static)

        if not message.results:
            loader_text.update(f'Nothing found for "[b]{message.query}[/b]"')
            return

        loader.add_class("hidden")
        table.remove_class("hidden")

        for idx, torrent in enumerate(message.results):
            table.add_row(
                idx + 1,
                torrent.title,
                human_readable_size(torrent.size),
                torrent.seeders,
                torrent.leechers,
                torrent.source,
                key=torrent.magnet_uri,
            )

        table.focus()

    @work(exclusive=True, thread=True)
    async def _download_torrent(self, magnet_uri: str) -> None:
        self.lt_session = lt.session()  # pyright: ignore
        self.lt_session.listen_on(6881, 6891)

        params = {
            "save_path": config.get("general.download_path"),
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,  # pyright: ignore
        }

        self.lt_handle = lt.add_magnet_uri(  # pyright: ignore
            self.lt_session, magnet_uri, params
        )

        self.app.call_from_thread(
            self._update_download_ui, "[b $success]Fetching Metadata...[/]", 0
        )

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
        self.query_one("#downloads_container Static", Static).update(status)
        self.query_one("#downloads_container ProgressBar", ProgressBar).update(
            progress=progress
        )

    def _get_client(self) -> Optional[JackettClient]:
        if not self.provider:
            return

        if self.provider.name == "Jackett":
            return JackettClient(url=self.provider.url, api_key=self.provider.api_key)
