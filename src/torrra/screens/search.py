from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Label, ListItem, ListView

from torrra.core.searcher import search_torrents


class SearchScreen(Screen):
    CSS_PATH = "search.tcss"

    def compose(self) -> ComposeResult:
        yield Vertical(
            Input(placeholder="Search...", id="search"),
            ListView(id="results_list"),
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#search", Input).blur()
        query = event.value
        if not query:
            return

        results = search_torrents(query)
        list_view = self.query_one("#results_list", ListView)
        list_view.focus()
        list_view.clear()
        for torrent in results:
            list_view.append(
                ListItem(
                    Label(
                        f"{torrent['name']} - {torrent['size']} - 🧲 {torrent['seeders']}"
                    )
                )
            )
