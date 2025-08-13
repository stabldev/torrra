# Installation

`torrra` offers several convenient methods for installation, allowing you to choose the approach that best fits your environment and preferences.

## Cross-Platform (Recommended)

For most users, `pipx` is the recommended installation method. It ensures `torrra` is installed in an isolated environment, preventing potential conflicts with your system's other Python packages.

```bash
pipx install torrra
```

This method supports **Linux**, **macOS**, and **Windows**. `libtorrent` (a core dependency for torrent management) is automatically installed via `pip` as part of this process.

## Arch Linux

If you are an Arch Linux user, `torrra` can be installed directly from the Arch User Repository (AUR).

### From AUR (builds from source)

This method compiles `torrra` from its source code, which might take a bit longer but ensures you have the latest features.

```bash
yay -S torrra
```

### From AUR Binary Package (faster installation)

For a quicker installation, you can use the precompiled binary package available on AUR. This option requires no Python dependencies on your system.

```bash
yay -S torrra-bin
```

> `torrra-bin` includes a precompiled standalone binary specifically for x86_64 Linux systems.

## Standalone Binaries (No Python Required)

You can download pre-built executables of `torrra` directly from the [GitHub Releases](https://github.com/stabldev/torrra/releases) page. These binaries do not require Python to be installed on your system.

| OS      | File                         |
| :------ | :--------------------------- |
| Linux   | `torrra-vX.Y.Z-linux-x86_64` |
| Windows | `torrra-vX.Y.Z-windows.exe`  |
| macOS   | `torrra-vX.Y.Z-macos-x86_64` |

> **Note:** On Linux and macOS, after downloading, you'll need to make the binary executable:
> `chmod +x torrra-vX.Y.Z-*-x86_64`
>
> (Replace `vX.Y.Z-*-x86_64` with the actual filename you downloaded.)

## Homebrew (macOS)

Thanks to community contribution, `torrra` is also available via [Homebrew](https://brew.sh/) for macOS users.

This method installs the precompiled binary version of `torrra`, avoiding the need for Python or any additional setup.

```bash
brew tap Maniacsan/homebrew-torrra
brew install torrra
```

## Docker

`torrra` is also available as a Docker image, providing an isolated and portable way to run the tool without installing its dependencies directly on your host system.

The official Docker image is hosted on Docker Hub: [`stabldev/torrra`](https://hub.docker.com/r/stabldev/torrra).

### Quick Usage

To run `torrra` with a specific indexer (e.g., `jackett`) without persistent configuration:

```bash
docker run --rm -it stabldev/torrra:latest jackett --url <url> --api-key <api_key>
```

> Remember to replace `jackett` with your chosen indexer option and provide the correct `--url` and `--api-key`. You will need to mount any required config or download directories if you need persistence.

### With Config and Downloads Folder Mounted

For persistent configuration and downloads, you should mount your local configuration directory into the Docker container. This example assumes your `config.toml` is located at `~/.config/torrra`.

```bash
docker run --rm -it \
  -v ~/.config/torrra:/root/.config/torrra \
  -v /path/to/your/downloads:/root/Downloads \
  stabldev/torrra:latest jackett --url <url> --api-key <api_key>
```

> Ensure your `config.toml` inside `~/.config/torrra` is set up correctly with a `download_path` pointing to `/downloads` inside the container if you want downloads to persist to `/path/to/your/downloads` on your host.

### Image Tags

- `stabldev/torrra:latest` - Always points to the most recent stable release.
- `stabldev/torrra:<version>` - For a specific release version (e.g., `stabldev/torrra:v1.2.3`).

## Local Development

If you intend to contribute to `torrra` or want to run it directly from its source code, follow these steps to set up your local development environment:

```bash
git clone [https://github.com/stabldev/torrra](https://github.com/stabldev/torrra)
cd torrra
uv sync # or `pip install -e .` (if you prefer pip)
uv run torrra
```
