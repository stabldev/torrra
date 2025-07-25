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

- [Features](#features)
- [Installation](#installation)
  - [Cross-Platform](#cross-platform-recommended)
  - [Arch Linux](#arch-linux)
  - [Standalone Binaries](#standalone-binaries-no-python-required)
  - [Docker](#docker)
  - [Local Development](#local-development)
- [Usage](#usage)
  - [Command-Line Interface (CLI)](#command-line-interface-cli)
  - [Text-User Interface (TUI) Controls](#text-user-interface-tui-controls)
- [Configuration](#configuration)
  - [Managing Your Configuration](#managing-your-configuration)
- [Indexer Support](#indexer-support)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

- Integrate with services like [`Jackett`](https://github.com/Jackett/Jackett) and [`Prowlarr`](https://github.com/Prowlarr/Prowlarr).
- Fetch and download magnet links directly, powered by [`Libtorrent`](https://libtorrent.org/).
- A responsive download manager built with [`Textual`](https://textual.textualize.io/).
- Pause and resume torrent downloads using keyboard shortcuts.
- Operates as both a `CLI` tool and a full-screen terminal `UI`.
- Toggle between dark and light themes.
- Opt-in caching for blazing fast repeated searches.

## Installation

`torrra` offers several installation methods to suit your environment.

### Cross-Platform (recommended)

Using `pipx` ensures `torrra` is installed in an isolated environment, preventing conflicts with your system's Python packages.

```bash
pipx install torrra
```

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

> `torrra-bin` includes a precompiled standalone binary for x86_64 Linux, requiring no Python dependencies.

### Standalone Binaries (No Python Required)

Download pre-built executables directly from [GitHub Releases](https://github.com/stabldev/torrra/releases):

| OS      | File                         |
| :------ | :--------------------------- |
| Linux   | `torrra-vX.Y.Z-linux-x86_64` |
| Windows | `torrra-vX.Y.Z-windows.exe`  |
| macOS   | `torrra-vX.Y.Z-macos-x86_64` |

> On Linux/macOS, ensure the binary is executable: `chmod +x torrra-vX.Y.Z-*-x86_64`.

### Docker

`torrra` is also available as a Docker image, allowing you to run it in an isolated environment without installing Python dependencies directly on your host system.

The official image is hosted on Docker Hub: [`stabldev/torrra`](https://hub.docker.com/r/stabldev/torrra).

#### Quick Usage

```bash
docker run --rm -it stabldev/torrra:latest jackett --url <url> --api-key <api_key>
```

> Replace `jackett` with your preferred indexer option.
> You must mount any required config or download directories if needed.

#### With Config and Downloads Folder Mounted

```bash
docker run --rm -it \
  -v ~/.config/torrra:/root/.config/torrra \
  stabldev/torrra:latest jackett --url <url> --api-key <api_key>
```

> Ensure your `config.toml` inside `~/.config/torrra` is set up correctly.

#### Image Tags

- `stabldev/torrra:latest` - always points to the latest release
- `stabldev/torrra:<version>` - for a specific release (e.g., `x.y.z`)

### Local Development

To set up `torrra` for development:

```bash
git clone https://github.com/stabldev/torrra
cd torrra
uv sync # or `pip install -e .`
uv run torrra
```

Here's an improved version of your `Usage` section, focusing on clarity, user-friendliness, and a logical flow.

## Usage

Specify an indexer and provide its connection details. For instance, to use [`Jackett`](https://github.com/Jackett/Jackett):

```bash
torrra jackett --url http://localhost:9117 --api-key <your_jackett_api_key>
```

> Replace `<your_jackett_api_key>` with your actual `Jackett` API key.

Similarly, for [`Prowlarr`](https://github.com/Prowlarr/Prowlarr):

```bash
torrra prowlarr --url http://localhost:9696 --api-key <your_prowlarr_api_key>
```

> Replace `<your_prowlarr_api_key>` with your actual `Prowlarr` API key.

### Command-Line Interface (CLI)

`torrra` offers a comprehensive CLI for managing configurations and launching the application with specific indexers.

| Command                 | Description                                                                                          |
| :---------------------- | :--------------------------------------------------------------------------------------------------- |
| `torrra`                | Displays the help message if no subcommand is provided                                               |
| `torrra --help`         | Shows the general help message                                                                       |
| `torrra --version`      | Displays the current installed version of `torrra`                                                   |
| `torrra config`         | Accesses the configuration subcommands                                                               |
| `torrra jackett`        | Initializes `torrra` using [`Jackett`](https://github.com/Jackett/Jackett) as the torrent indexer    |
| `torrra prowlarr`       | Initializes `torrra` using [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) as the torrent indexer |

#### `torrra config` Subcommands

| Subcommand                        | Description                                                            |
| :-------------------------------- | :--------------------------------------------------------------------- |
| `torrra config get <key>`         | Retrieves the value associated with a specific key                     |
| `torrra config set <key> <value>` | Sets a configuration key to a specified value                          |
| `torrra config list`              | Lists all currently set configuration values                           |

#### Indexer Options

Both `jackett` and `prowlarr` support:

- `--url` (Required): Indexer URL
- `--api-key` (Required): Your API key
- `--no-cache`: Disable caching
- `--help`: Show command help

### Text-User Interface (TUI) Controls

Once `torrra` is running, you'll interact with it through its intuitive TUI. Here are the keyboard controls:

| Key      | Action                                                                        |
| :------- | :---------------------------------------------------------------------------- |
| `↑` `↓`  | Navigate up and down through the list of search results                       |
| `Tab`    | Move focus to the next interactive widget                                     |
| `Enter`  | Initiate the download for the currently selected torrent                      |
| `p`      | Pause the currently active download                                           |
| `r`      | Resume a previously paused download                                           |
| `q`      | Quit `torrra`                                                                 |

## Configuration

`torrra`'s behavior can be customized via a `config.toml` file located in your OS-specific user config directory:

- **Linux/macOS:** `~/.config/torrra/config.toml`
- **Windows:** `%APPDATA%\torrra\config.toml`

> The actual path is automatically resolved using [`platformdirs`](https://pypi.org/project/platformdirs/).

Example `config.toml`:

```toml
[general]
download_path = "/home/username/Downloads"   # Default folder for saving torrents
remember_last_path = true                    # Reuse the last used path as default
```

### Managing Your Configuration

Use the built-in `torrra config` command to manage settings:

```bash
torrra config get general.download_path              # Get a specific config value
torrra config set general.remember_last_path false   # Set a key-value pair
torrra config list                                   # List all config settings
```

## Indexer Support

Currently supported:

- [`Jackett`](https://github.com/Jackett/Jackett)
- [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) (NOTE: check `"Prefer Magnet URL"` option)

Planned:

- Support for custom indexers

## Roadmap

Ongoing development focuses on enhancing `torrra`'s capabilities:

- [x] Jackett integration
- [x] Prowlarr support
- [x] Torrent download `UI` with pause/resume
- [x] Config file support
- [x] Standalone binary & AUR packaging
- [x] Magnet info preview (seeders/leechers before download)
- [ ] Advanced filtering/sorting
- [ ] Nyaa & anime-specific indexers
- [ ] Keyboard shortcuts overlay / help screen

## Contributing

`torrra` is an open-source project, and contributions are highly valued.

- If you find an issue, please [open an issue](https://github.com/stabldev/torrra/issues) with detailed steps to reproduce.
- We welcome new features or indexer integrations. Fork the repository and submit a Pull Request.
- General feedback and feature requests are always appreciated.

## License

**MIT License.** Copyright (c) [stabldev](https://github.com/stabldev)
