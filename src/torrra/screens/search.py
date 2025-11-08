import time
import webbrowser
from typing import Any, ClassVar, cast, override

import libtorrent as lt
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.types import CSSPathType
from textual.widgets import DataTable, Input, LoadingIndicator, ProgressBar, Static
from textual.widgets.data_table import ColumnKey

from torrra._types import Indexer, Torrent
from torrra.core.config import config
from torrra.indexers.utils import get_indexer
from torrra.utils.fs import get_resource_path
from torrra.utils.helpers import human_readable_size
from torrra.utils.magnet import resolve_magnet_uri


class SearchScreen(Screen[None]):
    CSS_PATH: ClassVar[CSSPathType | None] = get_resource_path("screens/search.css")
    # layout constants
    COLS: list[tuple[str, str, int]] = [
        ("No.", "no_col", 3),
        ("Title", "title_col", 25),
        ("Size", "size_col", 10),
        ("Seed", "seeders_col", 4),
        ("Leech", "leechers_col", 5),
        ("Source", "source_col", 6),
    ]

    class SearchResults(Message):
        def __init__(self, results: list[Torrent], query: str) -> None:
            self.results: list[Torrent] = results
            self.query: str = query
            super().__init__()

    class DownloadStatus(Message):
        def __init__(self, status: str, progress: float) -> None:
            self.status: str = status
            self.progress: float = progress
            super().__init__()

    def __init__(self, indexer: Indexer | None, query: str):
        super().__init__()
        self.indexer: Indexer | None = indexer
        self.search_query: str = query
        self.use_cache: bool = True  # TODO: read from config
        # libtorrent state
        self._lt_session: lt.session | None = None
        self._lt_handle: lt.torrent_handle | None = None
        self._lt_paused: bool = False
        # ui refs (cached later)
        self._search_input: Input
        self._table: DataTable[str]
        self._loader: Vertical
        self._loader_status: Static
        self._download_container: Container
        self._download_progressbar: ProgressBar
        self._download_status_label: Static

    # --------------------------------------------------
    # COMPOSE
    # --------------------------------------------------
    @override
    def compose(self) -> ComposeResult:
        with Vertical():
            # search input
            search_input = Input(
                placeholder="Search...", id="search", value=self.search_query
            )
            search_input.border_title = "[$secondary]s[/]earch"
            yield search_input
            # loading indicator
            with Vertical(id="loader"):
                yield Static(id="status")
                yield LoadingIndicator(id="indicator")
            # results data-table
            results_dt: DataTable[str] = DataTable(
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

    # --------------------------------------------------
    # MOUNT / UNMOUNT
    # --------------------------------------------------
    def on_mount(self) -> None:
        self._search_input = self.query_one("#search", Input)
        self._table = self.query_one("#results_table", DataTable)
        self._download_container = self.query_one("#downloads_container", Container)
        self._loader = self.query_one("#loader", Vertical)
        self._loader_status = self.query_one("#loader #status", Static)
        self._download_progressbar = self.query_one("#progressbar", ProgressBar)
        self._download_status_label = self._download_container.query_one(
            "#status", Static
        )

        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)
        # send initial search
        self.post_message(Input.Submitted(self._search_input, self.search_query))

    def on_unmount(self) -> None:
        # clean libtorrent session
        if self._lt_session and self._lt_handle:
            self._lt_session.remove_torrent(self._lt_handle, lt.options_t.delete_files)
        self._lt_session = None

    # --------------------------------------------------
    # UI ADJUSTMENTS / SHORTCUTS
    # --------------------------------------------------
    def on_resize(self) -> None:
        total_cell_padding = self._table.cell_padding * 2 * len(self._table.columns)
        # space taken for border and padding
        border_and_padding = 4
        cols_total_width_without_title = sum(w for t, _, w in self.COLS if t != "Title")
        title_col_width = (
            self.size.width
            - cols_total_width_without_title
            - total_cell_padding
            - border_and_padding
        )

        # make title column expand
        self._table.columns[ColumnKey("title_col")].width = title_col_width

    def key_s(self) -> None:
        self._search_input.focus()

    def key_p(self) -> None:
        if (
            not self._download_container.has_focus
            or not self._lt_handle
            or self._lt_paused
        ):
            return
        self._lt_handle.pause()
        self._lt_paused = True

    def key_r(self) -> None:
        if (
            not self._download_container.has_focus
            or not self._lt_handle
            or not self._lt_paused
        ):
            return
        self._lt_handle.resume()
        self._lt_paused = False

    # --------------------------------------------------
    # SEARCH LOGIC
    # --------------------------------------------------
    @on(Input.Submitted, "#search")
    def handle_search(self, event: Input.Submitted) -> None:
        query = event.value
        if not query:
            return

        self._table.add_class("hidden")
        self._table.clear()
        self._loader.remove_class("hidden")
        self._loader_status.update(f'Searching for: "[b]{query}[/]"')

        self._perform_search(query)

    @work(exclusive=True)
    async def _perform_search(self, query: str) -> None:
        indexer = get_indexer()
        results = []

        if indexer:
            try:
                results = await indexer.search(query, use_cache=self.use_cache)
            except Exception as e:
                self.log.error(f"error during search: {e}")
        self.post_message(self.SearchResults(results, query))

    @on(SearchResults)
    def _show_search_results(self, message: SearchResults) -> None:
        if not message.results:
            self._loader_status.update(f'Nothing found for "[b]{message.query}[/b]"')
            return

        self._loader.add_class("hidden")
        self._table.remove_class("hidden")
        self._table.focus()

        seen: set[str] = set()
        for idx, torrent in enumerate(message.results):
            if torrent.magnet_uri is None or torrent.magnet_uri in seen:
                continue

            seen.add(torrent.magnet_uri)
            self._table.add_row(
                str(idx + 1),
                torrent.title,
                human_readable_size(torrent.size),
                str(torrent.seeders),
                str(torrent.leechers),
                torrent.source,
                key=torrent.magnet_uri,
            )

    # --------------------------------------------------
    # SELECTION / DOWNLOAD
    # --------------------------------------------------
    @on(DataTable.RowSelected, "#results_table")
    async def handle_select(self, event: DataTable.RowSelected) -> None:
        magnet_uri = cast(str, event.row_key.value)
        self._search_input.disabled = True
        self._table.disabled = True
        self._update_download_status("[b $success]Fetching Metadata...[/]")

        resolved = await resolve_magnet_uri(magnet_uri)
        self._handle_magnet_uri(resolved)

    def _handle_magnet_uri(self, magnet_uri: str | None) -> None:
        if not magnet_uri:
            self._update_download_status("[$error]Invalid magnet URI[/]")
            return

        if config.get("general.download_in_external_client").lower() == "true":
            self._download_in_external_client(magnet_uri)
        else:
            self._download_in_libtorrent(magnet_uri)

    def _download_in_external_client(self, magnet_uri: str) -> None:
        if webbrowser.open(magnet_uri):
            self._update_download_status("[$error]Failed to open magnet URI[/]")
        else:
            self._update_download_status(
                "[$success]Magnet URI opened in external client[/]"
            )

    # --------------------------------------------------
    # LIBTORRENT DOWNLOAD
    # --------------------------------------------------
    @work(exclusive=True, thread=True)
    def _download_in_libtorrent(self, magnet_uri: str) -> None:
        self.query_one("#progressbar-and-actions", Horizontal).remove_class("hidden")

        self._lt_session = lt.session()
        self._lt_session.listen_on(6881, 6891)

        params: dict[str, Any] = {
            "save_path": config.get("general.download_path"),
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,
        }

        self._lt_handle = lt.add_magnet_uri(self._lt_session, magnet_uri, params)
        while not self._lt_handle.has_metadata():
            time.sleep(0.5)

        torrent_info = self._lt_handle.get_torrent_info()
        title = torrent_info.name()
        total_size = human_readable_size(torrent_info.total_size())

        status_template = (
            f"[b $secondary]Title: [$primary]{title}[/$primary] - "
            "Mode: [$success]{status}[/$success] - "
            "Seeds: {seeds} - "
            "Peers: {peers} - "
        )

        # downloading loop
        while not self._lt_handle.is_seed():
            s = self._lt_handle.status()
            msg = (
                status_template.format(
                    status="Paused" if self._lt_paused else "Download",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Size: {total_size}[/]"
            )

            self._update_download_status(msg, s.progress * 100)
            time.sleep(1)

        # seeding loop
        while True:
            s = self._lt_handle.status()
            msg = (
                status_template.format(
                    status="Paused" if self._lt_paused else "Seed",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Uploaded: {human_readable_size(s.total_upload)}[/]"
            )

            self._update_download_status(msg, 100)
            time.sleep(5)

    # --------------------------------------------------
    # DOWNLOAD STATUS UPDATES
    # --------------------------------------------------
    def _update_download_status(self, message: str, progress: float = 0) -> None:
        self.post_message(self.DownloadStatus(message, progress))

    @on(DownloadStatus)
    def on_download_status(self, message: DownloadStatus) -> None:
        self._download_status_label.update(message.status)
        self._download_progressbar.update(progress=message.progress)
