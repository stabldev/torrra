# Installation

Torrra offers multiple installation methods to suit different environments. Choose the option that best fits your system.

## Recommended Methods

### pipx (Cross-Platform)

For most users, we recommend installing with [pipx](https://pypa.github.io/pipx/), which provides isolated Python environments:

```bash
pipx install torrra
```

**Features:**

- Works on Linux, macOS, and Windows
- Automatically handles `libtorrent` dependency
- Prevents conflicts with system Python packages

**Requirements:**

- Python ≥ 3.13

<details>
<summary>Don't have pipx?</summary>

```bash
python -m pip install --user pipx
pipx ensurepath
```

</details>

## Alternative Methods

### Arch Linux

1. **Source build** (compiles during installation):

   ```bash
   yay -S torrra
   ```

2. **Precompiled binary** (faster installation):

   ```bash
   yay -S torrra-bin
   ```

   - No Python installation required
   - Standalone binary built with PyInstaller

### Standalone Binaries

Download pre-built executables from our [GitHub Releases](https://github.com/stabldev/torrra/releases).

**Post-download steps:**

```bash
chmod +x torrra-vX.Y.Z-*-x86_64  # Make executable
sudo mv torrra-vX.Y.Z-*-x86_64 /usr/local/bin/torrra  # Install to PATH
```

### Docker

Official images are available on [Docker Hub](https://hub.docker.com/r/stabldev/torrra).

**Basic usage:**

```bash
docker run --rm -it stabldev/torrra:latest jackett --url <url> --api-key <key>
```

**Persistent configuration:**

```bash
docker run --rm -it \
  -v ~/.config/torrra:/root/.config/torrra \
  stabldev/torrra:latest jackett --url <url> --api-key <key>
```

## Development Installation

For contributing to Torrra:

```bash
git clone https://github.com/stabldev/torrra
cd torrra
uv sync         # or: pip install -e .
uv run torrra   # or: torrra
```

## Verify Install

After installation, confirm it works:

```bash
torrra --version
```
