# torrra

> A Python tool that lets you find and download torrents without leaving your CLI.

[![PyPI](https://img.shields.io/pypi/v/torrra)](https://pypi.org/project/torrra/)
[![AUR Version](https://img.shields.io/aur/version/torrra)](https://aur.archlinux.org/packages/torrra)
[![GitHub release](https://img.shields.io/github/v/release/stabldev/torrra?sort=semver)](https://github.com/stabldev/torrra/releases)
[![License](https://img.shields.io/github/license/stabldev/torrra)](https://github.com/stabldev/torrra/blob/main/LICENSE)
[![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/stabldev/torrra)](https://github.com/stabldev/torrra/issues)

![demo](./docs/demo.gif)

## Features

- Use custom providers like [`Jackett`](https://github.com/Jackett/Jackett)
- Fetch and download magnet links using [`Libtorrent`](https://libtorrent.org/)
- TUI: Interactive download manager with [`Textual`](https://textual.textualize.io/)
- Pause/resume torrent downloads with keyboard
- Works as a CLI or full-screen terminal UI
- Toggle b/w `dark` and `light` theme

## Installation

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

> Make sure to `chmod +x` the binary if needed.

### Local Development

```bash
git clone https://github.com/stabldev/torrra
cd torrra
uv sync  # or `pip install -e .`
uv run torrra
```

## Usage

```bash
torrra --jackett
```

> Must provide a provider flag like `--jackett`. Otherwise, an error is shown.

### CLI Commands & Flags

#### Top-level commands

| Command          | Description                                        |
|------------------|----------------------------------------------------|
| `torrra`         | Launch the interactive TUI (requires a provider)   |
| `torrra config`  | Manage configuration (get/set/list)                |
| `torrra --help`  | Show help for the top-level CLI                    |

#### Provider flags (used with `torrra`)

| Flag                  | Description                                |
|-----------------------|--------------------------------------------|
| `-j`, `--jackett`     | Use Jackett as the torrent indexer         |
| `-v`, `--version`     | Show current version of Torrra             |
| `-h`, `--help`        | Show help for the main app                 |

### TUI Controls

| Key  | Action                        |
|------|-------------------------------|
| `↑↓` | Navigate results               |
| `Enter` | Start download for selection     |
| `p`  | Pause current download        |
| `r`  | Resume paused download        |
| `q`  | Quit Torrra                   |

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
```

### Usage

Use the built-in `torrra config` command to get or set configuration values:

```bash
torrra config -g general.download_path
torrra config -s general.remember_last_path False
torrra config -l
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

- [Jackett](https://github.com/Jackett/Jackett) (via `--jackett` or `-j`)

Planned:

- [Prowlarr](https://github.com/Prowlarr/Prowlarr)
- Custom indexers for optional support

## Roadmap

- [x] Jackett integration
- [x] Torrent download UI with pause/resume
- [x] Config file support
- [x] Standalone binary & AUR packaging
- [X] Magnet info preview (seeders/leechers before download)
- [ ] Prowlarr support
- [ ] Advanced filtering/sorting
- [ ] Nyaa & anime-specific indexers
- [ ] Keyboard shortcuts overlay / help

## Contributing

This is a passion project- contributions are welcome!

- Found a bug? [Open an issue](https://github.com/stabldev/torrra/issues)
- Want to add a new indexer? Fork and build!
- Feedback, feature requests, and PRs are all appreciated.

## License

MIT. Copyright (c) [stabldev](https://github.com/stabldev)
