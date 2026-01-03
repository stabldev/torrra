# Torrra - “rrr”

> A Python tool that lets you search and download torrents without leaving your CLI.

[![Python Versions](https://img.shields.io/pypi/pyversions/torrra?style=flat-square)](https://pypi.org/project/torrra/)
[![PyPI](https://img.shields.io/pypi/v/torrra?style=flat-square)](https://pypi.org/project/torrra/)
[![AUR Version](https://img.shields.io/aur/version/torrra?style=flat-square)](https://aur.archlinux.org/packages/torrra)
[![Pepy Total Downloads](https://img.shields.io/pepy/dt/torrra?style=flat-square&color=blue)](https://pypi.org/project/torrra/)
[![CI Status](https://img.shields.io/github/actions/workflow/status/stabldev/torrra/ci.yml?style=flat-square)](https://github.com/stabldev/torrra/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/torrra/badge/?version=latest&style=flat-square)](https://torrra.readthedocs.io/)
[![License](https://img.shields.io/github/license/stabldev/torrra?style=flat-square)](https://github.com/stabldev/torrra/blob/main/LICENSE)

![demo](./docs/_static/demo.gif)

_Torrra_ provides a streamlined command-line interface for torrent search and downloads, powered by Jackett/Prowlarr and Libtorrent. Built with Textual, it offers a beautiful
TUI with pause/resume support - all without leaving your terminal.

**Full documentation**: https://torrra.readthedocs.io/en/latest/

## Installation

```bash
pipx install torrra
# or uv tool install torrra
```

Other options: [`AUR`](https://aur.archlinux.org/packages/torrra), [`standalone binaries`](https://github.com/stabldev/torrra/releases), [`Homebrew`](https://github.com/Maniacsan/homebrew-torrra) or [`Docker`](https://hub.docker.com/r/stabldev/torrra).

[See full install options →](https://torrra.readthedocs.io/en/latest/installation.html)

## Quick Usage

### 1. Interactive Search

Launch `torrra` with an indexer.

```bash
torrra jackett --url http://localhost:9117 --api-key <your_api_key>
```

### 2. Direct Search

Or, search directly from your command line and see instant results.

```bash
torrra search "arch linux iso"
```

### 3. Direct Download

Download torrents directly from magnet URIs or .torrent files without searching:

```bash
torrra download "magnet:?xt=urn:btih:..."
# or torrra download "/path/to/file.torrent"
```

[Full Usage guide →](https://torrra.readthedocs.io/en/latest/usage.html)\
[See full CLI & TUI guide →](https://torrra.readthedocs.io/en/latest/usage.html#text-user-interface-tui-controls)

## Configuration

For persistent settings, `torrra` uses a `config.toml` file where you can configure your indexers, download paths, and themes. This avoids the need to pass arguments on every run.

For example, to set up Jackett as your default indexer:

```bash
# set your Jackett URL and API key
torrra config set indexers.jackett.url http://localhost:9117
torrra config set indexers.jackett.api_key <your_api_key>

# set Jackett as the default indexer
torrra config set indexers.default jackett
```

Now you can simply run `torrra` to start searching:

```bash
torrra
```

[Learn more about configuration →](https://torrra.readthedocs.io/en/latest/configuration.html)

## Features

- Search with [`Jackett`](https://github.com/Jackett/Jackett) or [`Prowlarr`](https://github.com/Prowlarr/Prowlarr)
- Download torrents directly with pause/resume support
- Beautiful and responsive TUI built with [`Textual`](https://textual.textualize.io/)
- Customizable themes (dark, light, and more)
- Smart config + opt-in caching for fast searches
- Native support for Linux, macOS, and Windows

[Full feature list →](https://torrra.readthedocs.io/en/latest/#features)

## Contributing

Contributions are welcome and greatly appreciated!\
Whether it's reporting a bug, submitting a feature request, or writing code, we value your help.

- **Found a bug or have an idea?** [Open an issue](https://github.com/stabldev/torrra/issues/new/choose) to let us know.
- **Want to contribute code?** Check out the [Contributing Guide](https://torrra.readthedocs.io/en/latest/contributing.html),\
  to learn how to set up your development environment and submit a pull request.

## License

[MIT](LICENSE) © 2025 ^\_^ [`@stabldev`](https://github.com/stabldev)

## Like my work?

This project needs a ⭐ from you. Don't forget to leave a ⭐\
If you found this helpful, consider supporting me with a coffee.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/stabldev)
