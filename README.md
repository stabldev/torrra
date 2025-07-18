# `torrra`

> A Python tool that lets you find and download torrents without leaving your CLI.

[![PyPI](https://img.shields.io/pypi/v/torrra)](https://pypi.org/project/torrra/)
[![AUR Version](https://img.shields.io/aur/version/torrra)](https://aur.archlinux.org/packages/torrra)
[![GitHub release](https://img.shields.io/github/v/release/stabldev/torrra?sort=semver)](https://github.com/stabldev/torrra/releases)
[![License](https://img.shields.io/github/license/stabldev/torrra)](https://github.com/stabldev/torrra/blob/main/LICENSE)
[![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/stabldev/torrra)](https://github.com/stabldev/torrra/issues)

![demo](./docs/demo.gif)

## Overview

`torrra` provides a streamlined command-line interface for your torrent needs. It allows you to search for and download torrents, and manage active downloads without leaving your terminal, offering a fast and efficient solution for command-line users.

## Table of Contents

* [Features](#features)
* [Installation](#installation)
    * [Cross-Platform](#cross-platform-recommended)
    * [Arch Linux](#arch-linux)
    * [Standalone Binaries](#standalone-binaries-no-python-required)
    * [Local Development](#local-development)
* [Usage](#usage)
    * [CLI Commands & Flags](#cli-commands--flags)
    * [TUI Controls](#tui-controls)
* [Configuration](#configuration)
    * [Managing Your Configuration](#managing-your-configuration)
    * [Config Options](#config-options)
* [Indexer Support](#indexer-support)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)

## Features

* Integrate with services like [`Jackett`](https://github.com/Jackett/Jackett).
* Fetch and download magnet links directly, powered by [`Libtorrent`](https://libtorrent.org/).
* A responsive download manager built with [`Textual`](https://textual.textualize.io/).
* Pause and resume torrent downloads using keyboard shortcuts.
* Operates as both a `CLI` tool and a full-screen terminal `UI`.
* Toggle between dark and light themes.

## Installation

`torrra` offers several installation methods to suit your environment.

### Cross-Platform (recommended)

Using `pipx` ensures `torrra` is installed in an isolated environment, preventing conflicts with your system's Python packages.

```bash
pipx install torrra
````

> This method supports **Linux**, **macOS**, and **Windows**. `libtorrent` is installed automatically via pip.

### Arch Linux

1. **From AUR (builds from source):**
```bash
yay -S torrra
```
2. **From AUR Binary Package (faster installation):**
```bash
yay -S torrra-bin
```
> `torrra-bin` includes a precompiled standalone binary for x86\_64 Linux, requiring no Python dependencies.

### Standalone Binaries (No Python Required)

Download pre-built executables directly from [GitHub Releases](https://github.com/stabldev/torrra/releases):

| OS      | File                                |
| :------ | :---------------------------------- |
| Linux   | `torrra-vX.Y.Z-linux-x86_64`        |
| Windows | `torrra-vX.Y.Z-windows.exe`         |
| macOS   | `torrra-vX.Y.Z-macos-x86_64`        |

> On Linux/macOS, ensure the binary is executable: `chmod +x torrra-vX.Y.Z-*-x86_64`.

### Local Development

To set up `torrra` for development:

```bash
git clone [https://github.com/stabldev/torrra](https://github.com/stabldev/torrra)
cd torrra
uv sync # or `pip install -e .`
uv run torrra
```

## Usage

To start `torrra`, you must specify a provider. For example, to use [Jackett](https://github.com/Jackett/Jackett):

```bash
torrra --jackett
```

> Omitting a provider flag will result in an error.

### CLI Commands & Flags

#### Top-level commands

| Command         | Description                                     |
| :-------------- | :---------------------------------------------- |
| `torrra`        | Launches the interactive TUI                    |
| `torrra config` | Manages configuration settings                  |
| `torrra --help` | Displays help for the top-level CLI commands    |

#### Provider flags (used with `torrra`)

| Flag              | Description                               |
| :---------------- | :---------------------------------------- |
| `-j`, `--jackett` | Uses Jackett as the torrent indexer       |
| `-v`, `--version` | Shows the current `torrra` version        |
| `-h`, `--help`    | Displays help for the main application    |

### TUI Controls

| Key     | Action                          |
| :------ | :------------------------------ |
| `↑↓`    | Navigate through results        |
| `Tab`   | Focus the next widget           |
| `Enter` | Start download for selection    |
| `p`     | Pause the current download      |
| `r`     | Resume a paused download        |
| `q`     | Quit `torrra`                   |


## Configuration

`torrra`'s behavior can be customized via a `config.toml` file located in your OS-specific user config directory:

  * **Linux/macOS:** `~/.config/torrra/config.toml`
  * **Windows:** `%APPDATA%\torrra\config.toml`

> The actual path is automatically resolved using [platformdirs](https://pypi.org/project/platformdirs/).

Example `config.toml`:

```toml
[general]
download_path = "/home/username/Downloads"   # Default folder for saving torrents
remember_last_path = true                    # Reuse the last used path as default
```

### Managing Your Configuration

Use the built-in `torrra config` command to manage settings:

```bash
torrra config -g general.download_path             # Get a specific config value
torrra config -s general.remember_last_path False  # Set a key-value pair
torrra config -l                                   # List all config settings
```

#### Config Options

| Flag              | Description                                   |
| :---------------- | :-------------------------------------------- |
| `-g`, `--get KEY` | Retrieves a config value (e.g., `general.download_path`) |
| `-s`, `--set KEY VALUE` | Sets a key-value pair                     |
| `-l`, `--list`    | Lists all configuration settings              |
| `-h`, `--help`    | Displays help for the config command          |


## Indexer Support

Currently supported:

  * [**Jackett**](https://github.com/Jackett/Jackett) (via `--jackett` or `-j`)

Planned:

  * [Prowlarr](https://github.com/Prowlarr/Prowlarr)
  * Support for custom indexers

## Roadmap

Ongoing development focuses on enhancing `torrra`'s capabilities:

  * [x] Jackett integration
  * [x] Torrent download `UI` with pause/resume
  * [x] Config file support
  * [x] Standalone binary & AUR packaging
  * [X] Magnet info preview (seeders/leechers before download)
  * [ ] Prowlarr support
  * [ ] Advanced filtering/sorting
  * [ ] Nyaa & anime-specific indexers
  * [ ] Keyboard shortcuts overlay / help screen

## Contributing

`torrra` is an open-source project, and contributions are highly valued.

  * If you find an issue, please [open an issue](https://github.com/stabldev/torrra/issues) with detailed steps to reproduce.
  * We welcome new features or indexer integrations. Fork the repository and submit a Pull Request.
  * General feedback and feature requests are always appreciated.

## License

**MIT License.** Copyright (c) [stabldev](https://github.com/stabldev)
