from textual.app import App, ComposeResult
from textual.widgets import ProgressBar, Static

from torrra.widgets.details_panel import DetailsPanel


class DetailsPanelTestApp(App[None]):
    def __init__(self, show_progress_bar: bool = False) -> None:
        super().__init__()
        self.show_progress_bar = show_progress_bar

    def compose(self) -> ComposeResult:
        yield DetailsPanel(show_progress_bar=self.show_progress_bar)


async def test_details_panel_without_progress_bar():
    app = DetailsPanelTestApp(show_progress_bar=False)
    async with app.run_test() as pilot:
        panel = app.query_one(DetailsPanel)
        assert panel.has_class("hidden")
        assert len(panel.query(ProgressBar)) == 0
        assert len(panel.query("#details_eta")) == 0

        panel.update_content("Test info")
        content = panel.query_one("#details_content", Static)
        assert "Test info" in str(content.content)

        # escape closes the panel
        panel.remove_class("hidden")
        panel.focus()
        await pilot.press("escape")
        assert panel.has_class("hidden")


async def test_details_panel_with_progress_bar_and_eta():
    app = DetailsPanelTestApp(show_progress_bar=True)
    async with app.run_test():
        panel = app.query_one(DetailsPanel)
        assert len(panel.query(ProgressBar)) == 1
        assert len(panel.query("#details_eta")) == 1
        assert len(panel.query("#details_shortcuts")) == 1

        panel.update_content(
            "Torrent Details",
            progress=65.5,
            eta="12m 30s",
            shortcuts="[p] pause · [d] delete",
        )
        content = panel.query_one("#details_content", Static)
        progress_bar = panel.query_one(ProgressBar)
        eta_widget = panel.query_one("#details_eta", Static)
        shortcuts_widget = panel.query_one("#details_shortcuts", Static)

        assert "Torrent Details" in str(content.content)
        assert progress_bar.progress == 65.5
        assert "ETA:" in str(eta_widget.content)
        assert "12m 30s" in str(eta_widget.content)
        assert "[p] pause · [d] delete" in str(shortcuts_widget.content)
