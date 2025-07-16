from typing import Optional

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, LoadingIndicator, Static

from torrra._types import Provider
from torrra.providers.jackett import JackettClient
from torrra.utils.helpers import human_readable_size


class SearchScreen(Screen):
    CSS_PATH = "search.css"

    def __init__(self, provider: Optional[Provider], initial_query: str):
        super().__init__()
        self.provider = provider
        self.initial_query = initial_query

    def compose(self) -> ComposeResult:
        search_input = Input(
            placeholder="Search...", id="search", value=self.initial_query
        )
        search_input.border_title = "s"

        with Vertical():
            yield search_input
            with Vertical(id="loader"):
                yield Static()
                yield LoadingIndicator()
            yield DataTable(
                id="results_table",
                cursor_type="row",
                show_cursor=True,
                cell_padding=2,
                classes="hidden",
            )

    def on_mount(self) -> None:
        self.post_message(
            Input.Submitted(self.query_one("#search", Input), self.initial_query)
        )

        table = self.query_one("#results_table", DataTable)
        table.add_columns("No.", "Title", "Size", "Seeders", "Peers", "Tracker")

    def on_key(self, event: events.Key) -> None:
        if event.key == "s":
            self.query_one("#search", Input).focus()

    @on(Input.Submitted, "#search")
    async def handle_search(self, event: Input.Submitted) -> None:
        self.query_one("#search", Input).blur()
        table = self.query_one("#results_table", DataTable)
        loader = self.query_one("#loader", Vertical)
        loader_text = self.query_one("#loader Static", Static)

        query = event.value
        if not query:
            return

        loader_text.update(f'[b]Searching for:[/] "{query}"')
        client = self._get_client()

        if not client:
            # TODO: fallback build-in scrapers
            return

        results = await client.search(query)
        if not results:
            return

        loader.add_class("hidden")
        table.remove_class("hidden")

        table.clear()
        table.focus()

        for idx, torrent in enumerate(results):
            table.add_row(
                idx + 1,
                torrent["Title"],
                human_readable_size(torrent["Size"]),
                torrent["Seeders"],
                torrent["Peers"],
                torrent["Tracker"],
            )

    def _get_client(self) -> Optional[JackettClient]:
        if not self.provider:
            return

        if self.provider.name == "Jackett":
            return JackettClient(url=self.provider.url, api_key=self.provider.api_key)
