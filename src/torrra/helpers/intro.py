from rich.box import ASCII
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from torrra._version import __version__

console = Console()


def show_welcome():
    title = Text("torrra", style="bold magenta", justify="center")
    desc = Text(f"v{__version__}", style="dim", justify="center")

    body = Text(
        "\n".join(
            [
                "Find and download torrents right from your terminal.",
                "Powered by libtorrent and Python ❤️",
            ]
        ),
        justify="center",
    )

    panel = Panel.fit(
        body, title=title, subtitle=desc, border_style="bright_blue", box=ASCII
    )

    console.print(panel)

    footer = Text(justify="center")
    footer.append("* GitHub: ", style="bold")
    footer.append("https://github.com/stabldev/torrra\n", style="cyan underline")

    footer.append("* Report issues: ", style="bold")
    footer.append("https://github.com/stabldev/torrra/issues\n", style="cyan underline")

    footer.append("* Tip: ", style="green bold")
    footer.append("Use ↑/↓ to navigate, Enter to select", style="green")

    console.print(footer)
    console.print()
