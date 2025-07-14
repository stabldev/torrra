# torrra

> A Python tool that lets you find and download torrents without leaving your CLI.

[![PyPI](https://img.shields.io/pypi/v/torrra)](https://pypi.org/project/torrra/)
[![AUR Version](https://img.shields.io/aur/version/torrra)](https://aur.archlinux.org/packages/torrra)
[![GitHub release](https://img.shields.io/github/v/release/stabldev/torrra?sort=semver)](https://github.com/stabldev/torrra/releases)
[![License](https://img.shields.io/github/license/stabldev/torrra)](https://github.com/stabldev/torrra/blob/main/LICENSE)
[![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/stabldev/torrra)](https://github.com/stabldev/torrra/issues)

![demo](./docs/demo.gif)

## Features

- Search torrents from multiple indexers
- Fetch magnet links directly
- Download torrents via libtorrent
- Pretty CLI with Rich-powered progress bars
- Modular and easily extensible indexer architecture

## Installation

> Requires **Python 3.13+**. For torrent support, [libtorrent](https://libtorrent.org/) is needed (see options below).

### Recommended (cross-platform)

```bash
pipx install torrra
```

- Works on **Linux**, **macOS**, and **Windows**
- Uses `libtorrent` installed via pip

### Arch Linux

#### 1. From AUR (builds from source)

```bash
yay -S torrra
```

#### 2. From AUR binary package (faster install, no Python deps)

```bash
yay -S torrra-bin
```

> `torrra-bin` includes a precompiled standalone binary for x86_64 Linux.

### Standalone Binaries (no Python needed)

Download from the [GitHub Releases](https://github.com/stabldev/torrra/releases):

| OS       | File                          |
|----------|-------------------------------|
| Linux    | `torrra-vX.Y.Z-linux-x86_64`  |
| Windows  | `torrra-vX.Y.Z-windows.exe`   |
| macOS    | `torrra-vX.Y.Z-macos-x86_64`  |

Make sure to `chmod +x` the binary if needed.

### Local Development

```bash
git clone https://github.com/stabldev/torrra
cd torrra
uv sync  # or `pip install -e .`
uv run torrra
```

## Configuration

`torrra` lets you customize its behavior using a simple config file stored in the **user config directory** specific to your OS:

- **Linux/macOS:** `~/.config/torrra/config.toml`
- **Windows:** `%APPDATA%\torrra\config.toml`

> The actual path is resolved automatically using [platformdirs](https://pypi.org/project/platformdirs/), so you don’t need to worry about it.

Example:

```toml
[general]
download_path = "/home/username/Downloads"     # default folder to save torrents
remember_last_path = true                      # reuse last used path as default
max_results = 5                                # max number of results to show after search
```

> **Note:** Some indexers (like YTS) may return multiple magnet links per result (e.g., different qualities for the same movie).  
So if `max_results` is set to `2`, you might still see more than 2 magnet options depending on the indexer's structure.

### Usage

Use the built-in `torrra config` command to get or set configuration values:

```bash
torrra config -g general.download_path         # get a specific value
torrra config -s general.max_results 10        # set a value
torrra config -l                               # list all current config values
```

### Options

| Flag                  | Description                                |
|-----------------------|--------------------------------------------|
| `-g`, `--get KEY`     | get a config value (e.g., `general.max_results`) |
| `-s`, `--set KEY VALUE` | set a key-value pair                       |
| `-l`, `--list`        | list all config settings                   |
| `-h`, `--help`        | show help for the config command           |

## Indexer Support

Currently supported:

- YTS (movies)
- MagnetDL
- Movierulz (movies)

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
