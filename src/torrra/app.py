import sys
from typing import Optional

from textual import work
from textual.app import App

from torrra._types import Provider
from torrra.commands.config import handle_config_command
from torrra.core.exceptions import ConfigError
from torrra.screens.search import SearchScreen
from torrra.screens.welcome import WelcomeScreen
from torrra.utils.cli import parse_cli_args
from torrra.utils.fs import get_resource_path
from torrra.utils.provider import load_provider, load_provider_from_args


class TorrraApp(App):
    TITLE = "torrra"
    CSS_PATH = get_resource_path("app.css")
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark_mode", "Toggle dark mode"),
        ("escape", "clear_focus", "Clear focus"),
    ]
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, provider: Optional[Provider]) -> None:
        super().__init__()
        self.provider = provider

    @work
    async def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"

        if query := await self.push_screen_wait(WelcomeScreen(provider=self.provider)):
            search_screen = SearchScreen(provider=self.provider, initial_query=query)
            await self.push_screen(search_screen)

    def action_toggle_dark_mode(self) -> None:
        self.theme = (
            "catppuccin-mocha"
            if self.theme == "catppuccin-latte"
            else "catppuccin-latte"
        )

    def action_clear_focus(self) -> None:
        self.set_focus(None)


def main():
    args = parse_cli_args()
    provider = None

    try:
        if args.jackett is not None:
            if len(args.jackett) == 0:
                provider = load_provider("jackett")
            elif len(args.jackett) == 2:
                url, api_key = args.jackett
                provider = load_provider_from_args("jackett", url, api_key)
            else:
                print(
                    "[error] --jackett expects either no args or exactly 2: URL API_KEY"
                )
                sys.exit(1)
        elif args.prowlarr is not None:
            if len(args.prowlarr) == 0:
                provider = load_provider("prowlarr")
            elif len(args.prowlarr) == 2:
                url, api_key = args.prowlarr
                provider = load_provider_from_args("prowlarr", url, api_key)
            else:
                print(
                    "[error] --prowlarr expects either no args or exactly 2: URL API_KEY"
                )
                sys.exit(1)
        elif args.command == "config":
            handle_config_command(args)
            sys.exit()

        if not provider:
            print(
                "[error] no provider specified\n"
                "run torrra --help for more information",
            )
            sys.exit(1)

        app = TorrraApp(provider=provider)
        app.run()

    except (FileNotFoundError, RuntimeError, ConfigError) as e:
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
