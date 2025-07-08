# `torrra`

> A Python tool that lets you find and download torrents without leaving your CLI.

![PyPI](https://img.shields.io/pypi/v/torrra)
![Python](https://img.shields.io/pypi/pyversions/torrra)
![License](https://img.shields.io/github/license/stabldev/torrra)

![demo](./docs/demo.gif)

## Features

- Search torrents from multiple indexers (`YTS` supported; more coming)
- Fetch magnet links directly
- Download torrents via libtorrent
- Pretty CLI with Rich-powered progress bars
- Modular and easily extensible indexer architecture

## Installation

Requirements: Python 3.11+ and [libtorrent](https://libtorrent.org/) (choose an installation method below)

### All-in-one installation

```bash
pipx install "torrra[libtorrent]"
```

> Works on all platforms using the pip-installed libtorrent.

### For system package users

```bash
# arch
sudo pacman -S libtorrent-rasterbar
# debian/ubuntu
sudo apt install python3-libtorrent
# macOS (homebrew)
brew install libtorrent-rasterbar

# then install torrra with system lib access:
pipx install --system-site-packages torrra
```

### Basic pip installation (for venv)

```bash
pip install "torrra[libtorrent]"
```

### Windows-specific

```bash
pip install "torrra[libtorrent]"
# or using system libtorrent (if available):
pip install --system "torrra"
```

### OR: compile from source (advanced)

See libtorrent's build guide:
https://libtorrent.org/building.html

### Notes

- The `[libtorrent]` extra installs the Python wheel version of libtorrent.
- Using system packages (like `pacman`, `apt`, `brew`) may provide better performance.
- Use `--system-site-packages` only if you already have system-wide libtorrent installed.

### For local development:

```bash
git clone https://github.com/yourusername/torrra
cd torrra
# or use requirements.txt
uv sync
uv run torrra
```

## Usage

```bash
torrra
```

Follow the prompts:

1. Enter search query
2. Pick an indexer
3. Select a torrent
4. Choose quality / magnet link
5. Pick a download folder

## Indexer Support

Currently supported:

- YTS (movies)

Planned:

- 1337x
- GLodls
- Nyaa (anime-only, optional)
- Community-driven additions

## Dev Notes

- Modular indexer structure (`torrra/indexers`)
- Extend `BaseIndexer` to add new sources
- Built using:
  - `httpx` + `selectolax` for scraping
  - `libtorrent` for torrenting
  - `rich` for CLI visuals
  - `questionary` for input prompts

## Contributing & Notes

This project is a weekend-hacker side project- built for fun and learning. It's not a polished product (yet), but it works well enough for daily use!

If you run into any bugs, have suggestions, or want to help improve it, feel free to [open an issue](https://github.com/stabldev/torrra/issues) or even send a pull request. All contributions are welcome.

## License

MIT. Copyright (c) [stabldev](https://github.com/stabldev)
