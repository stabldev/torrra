import threading
import time
import webbrowser
from contextlib import suppress
from typing import TYPE_CHECKING, Any, ClassVar, cast
from typing_extensions import override

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Input, ProgressBar, Static

from torrra._types import Indexer, Torrent
from torrra.core.config import config
from torrra.indexers.base import BaseIndexer
from torrra.utils.helpers import human_readable_size, lazy_import
from torrra.utils.magnet import resolve_magnet_uri
from torrra.widgets.data_table import AutoResizingDataTable
from torrra.widgets.spinner import SpinnerWidget

if TYPE_CHECKING:
    import libtorrent as lt


class SearchScreen(Screen[None]):
    COLS: list[tuple[str, str, int]] = [
        ("No.", "no_col", 3),
        ("Title", "title_col", 25),
        ("Size", "size_col", 10),
        ("Seed", "seeders_col", 4),
        ("Leech", "leechers_col", 5),
        ("Source", "source_col", 6),
    ]

    # class-level constants
    METADATA_INTERVAL: ClassVar[float] = 0.5
    DOWNLOAD_SEED_INTERVAL: ClassVar[float] = 1.0

    # class-level caches
    _indexer_instance_cache: BaseIndexer | None = None

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

    def __init__(self, indexer: Indexer, search_query: str, use_cache: bool):
        super().__init__()
        self.indexer: Indexer = indexer
        self.search_query: str = search_query
        self.use_cache: bool = use_cache

        # libtorrent state
        self._lt_session: lt.session | None = None
        self._lt_handle: lt.torrent_handle | None = None

        # application states
        self._pause_event: threading.Event = threading.Event()
        self._stop_event: threading.Event = threading.Event()

        # ui refs (cached later)
        self._search_input: Input
        self._table: AutoResizingDataTable[str]
        self._loader_container: Vertical
        self._loader_status: Static
        self._loader_spinner: SpinnerWidget
        self._download_container: Container
        self._download_status_label: Static
        self._download_progressbar: ProgressBar
        self._download_progressbar_and_actions: Horizontal

    # --------------------------------------------------
    # COMPOSE
    # --------------------------------------------------
    @override
    def compose(self) -> ComposeResult:
        with Vertical(id="search_container"):
            yield Input(placeholder="Search...", id="search", value=self.search_query)
            with Vertical(id="loader"):
                yield Static(id="status")
                yield SpinnerWidget(name="shark", id="spinner")
            yield AutoResizingDataTable(
                id="results_table",
                cursor_type="row",
                show_cursor=True,
                cell_padding=2,
                classes="hidden",
            )
            with Container(id="downloads_container"):
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
        self._search_input.border_title = "[$secondary]s[/]earch"

        self._table = self.query_one("#results_table", AutoResizingDataTable)
        self._table.expand_col = "title_col"
        self._table.border_title = "[$secondary]r[/]esults"

        self._download_container = self.query_one("#downloads_container", Container)
        self._download_container.border_title = "[$secondary]d[/]ownloads"
        self._download_container.can_focus = True

        self._loader_container = self.query_one("#loader", Vertical)
        self._loader_status = self.query_one("#loader #status", Static)
        self._loader_spinner = self.query_one("#spinner", SpinnerWidget)
        self._download_status_label = self._download_container.query_one(
            "#status", Static
        )
        self._download_progressbar = self.query_one("#progressbar", ProgressBar)
        self._download_progressbar_and_actions = self.query_one(
            "#progressbar-and-actions", Horizontal
        )

        # setup table
        for label, key, width in self.COLS:
            self._table.add_column(label, width=width, key=key)

        # send initial search
        self.post_message(Input.Submitted(self._search_input, self.search_query))

    def on_unmount(self) -> None:
        self._stop_event.set()

        # clean libtorrent session
        if self._lt_session and self._lt_handle:
            with suppress(Exception):
                self._lt_session.remove_torrent(self._lt_handle)

        # RAII cleanup
        self._lt_session = None

    # --------------------------------------------------
    # UI ADJUSTMENTS / SHORTCUTS
    # --------------------------------------------------
    def key_s(self) -> None:
        self._search_input.focus()

    def key_p(self) -> None:
        if (
            not self._download_container.has_focus
            or not self._lt_handle
            or self._pause_event.is_set()
        ):
            return
        self._lt_handle.pause()
        self._pause_event.set()

    def key_r(self) -> None:
        if (
            not self._download_container.has_focus
            or not self._lt_handle
            or not self._pause_event.is_set()
        ):
            return
        self._lt_handle.resume()
        self._pause_event.clear()

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
        self._loader_container.remove_class("hidden")
        self._loader_spinner.resume()
        self._loader_status.update(f"Searching for [b]{query}[/b]...")

        self._perform_search(query)

    @work(exclusive=True)
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
        if not message.results:
            self._loader_status.update(f"Nothing Found for [b]{message.query}[/b]")
            self._loader_spinner.pause()
            return

        self._loader_container.add_class("hidden")
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
    @on(AutoResizingDataTable.RowSelected, "#results_table")
    async def handle_select(self, event: AutoResizingDataTable.RowSelected) -> None:
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

        if config.get("general.download_in_external_client"):
            self._download_in_external_client(magnet_uri)
        else:
            self._download_in_libtorrent(magnet_uri)

    def _download_in_external_client(self, magnet_uri: str) -> None:
        if not webbrowser.open(magnet_uri):
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
        import libtorrent as lt

        self._lt_session = lt.session()
        self._lt_session.listen_on(6881, 6891)

        params: dict[str, Any] = {
            "save_path": config.get("general.download_path"),
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,
        }

        self._lt_handle = lt.add_magnet_uri(self._lt_session, magnet_uri, params)

        while not self._lt_handle.has_metadata():
            if self._stop_event.is_set():
                return
            time.sleep(self.METADATA_INTERVAL)

        torrent_info = self._lt_handle.get_torrent_info()
        title = torrent_info.name()
        total_size = human_readable_size(torrent_info.total_size())

        download_status_str = (
            f"[b $secondary]Title: [$primary]{title}[/$primary] - "
            "Mode: [$success]{status}[/$success] - "
            "Seeds: {seeds} - "
            "Peers: {peers} - "
        )

        self._download_progressbar_and_actions.remove_class("hidden")
        # downloading loop
        while not self._lt_handle.is_seed():
            if self._stop_event.is_set():
                return

            s = self._lt_handle.status()
            msg = (
                download_status_str.format(
                    status="Paused" if self._pause_event.is_set() else "Download",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Size: {total_size}[/]"
            )

            self._update_download_status(msg, s.progress * 100)
            time.sleep(self.DOWNLOAD_SEED_INTERVAL)

        # seeding loop
        seed_ratio = config.get("general.seed_ratio", None)
        # ensure seed_ratio is a valid number, otherwise default to infinite seeding
        if not isinstance(seed_ratio, (int, float)) or seed_ratio < 0:
            seed_ratio = None

        while not self._stop_event.is_set():
            s = self._lt_handle.status()

            # check if seed ratio is reached
            if seed_ratio is not None and s.total_payload_download > 0:
                # calculate current ratio: uploaded / downloaded
                current_ratio = s.total_payload_upload / s.total_payload_download
                if current_ratio >= seed_ratio:
                    self._update_download_status(
                        f"[b $success]Seeding complete! Reached target ratio of {seed_ratio:.2f}[/]",
                        100,
                    )
                    time.sleep(self.DOWNLOAD_SEED_INTERVAL)
                    break

            msg = (
                download_status_str.format(
                    status="Paused" if self._pause_event.is_set() else "Seed",
                    seeds=s.num_seeds,
                    peers=s.num_peers,
                )
                + f"Uploaded: {human_readable_size(s.total_payload_upload)}[/]"
            )

            self._update_download_status(msg, 100)
            time.sleep(self.DOWNLOAD_SEED_INTERVAL)

    # --------------------------------------------------
    # DOWNLOAD STATUS UPDATES
    # --------------------------------------------------
    def _update_download_status(self, message: str, progress: float = 0) -> None:
        self.post_message(self.DownloadStatus(message, progress))

    @on(DownloadStatus)
    def on_download_status(self, message: DownloadStatus) -> None:
        self._download_status_label.update(message.status)
        self._download_progressbar.update(progress=message.progress)

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------
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
