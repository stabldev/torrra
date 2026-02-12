# Configuration

`torrra`'s behavior can be customized through a `config.toml` file, allowing you to set default paths, indexers, preferences, and other operational parameters.

## Configuration File Location

The `config.toml` file is automatically created in your operating system's standard user configuration directory. This ensures `torrra` follows best practices for application data storage.

The precise location varies by OS:

- **Linux/macOS:** `~/.config/torrra/config.toml`
- **Windows:** `%APPDATA%\torrra\config.toml`

> The actual path is automatically resolved by `torrra` using the `platformdirs` Python library.

## Example `config.toml`

Here's an example of what your `config.toml` might look like:

```toml
[general]
download_path = "/home/user/Downloads"    # Default folder for saved torrents
theme = "textual-dark"                        # Application theme
use_cache = true                              # Cache search results
cache_ttl = 300                               # Cache time-to-live in seconds
seed_ratio = 1.5                              # Seeding ratio limit

[download]
client = "internal"                           # "internal", "transmission", or "qbittorrent"

[downloaders.transmission]
host = "localhost"
port = 9091
username = "your_username"
password = "your_password"

[downloaders.qbittorrent]
host = "localhost"
port = 8080
username = "your_username"
password = "your_password"

[indexers]
default = "jackett"                           # Default indexer

[indexers.jackett]
url = "http://localhost:9117"                 # Jackett URL
api_key = "your-jackett-api-key"              # Jackett API key

[indexers.prowlarr]
url = "http://localhost:9696"                 # Prowlarr URL
api_key = "your-prowlarr-api-key"             # Prowlarr API key

```

You can create or edit this file manually with a text editor.

### Theme Configuration

You can change the look and feel of `torrra` by setting the `theme` option in the `[general]` section of your `config.toml`.

The available themes are:

- `catppuccin-latte`
- `catppuccin-mocha`
- `dracula`
- `flexoki`
- `gruvbox`
- `monokai`
- `nord`
- `solarized-light`
- `textual-ansi`
- `textual-dark` (default)
- `textual-light`
- `tokyo-night`

To use a different theme (e.g., `gruvbox`), you can either edit your `config.toml` file:

```toml
[general]
theme = "gruvbox"
```

Or, you can set it directly from the command line:

```bash
torrra config set general.theme gruvbox
```

### Indexer Selection

`torrra` supports configuring multiple torrent indexers (e.g., **Jackett**, **Prowlarr**) in the config file. At runtime, you can:

Use the default indexer by simply running:

```bash
torrra
```

Override the default by specifying the indexer name:

```bash
torrra jackett
```

This will use the configuration under `[indexers.jackett]`.
If the selected indexer is not defined in the config file, `torrra` will show an error and exit.

## Managing Your Configuration via CLI

`torrra` provides built-in command-line tools to inspect and modify your configuration settings without directly editing the `config.toml` file. This is particularly useful for scripting or quick adjustments.

Use the `torrra config` subcommand followed by `get`, `set`, or `list`.

### Retrieving a Configuration Value

To get the value associated with a specific key:

```bash
torrra config get general.download_path
```

This command would output the currently configured download path.

### Setting a Configuration Value

To set a configuration key to a new value:

```bash
torrra config set download.client transmission
```

This would change the download client to "transmission". Note that boolean values (true/false) should be provided as such, and strings should be enclosed in quotes if they contain spaces or special characters (though for simple paths, it might not always be necessary depending on your shell).

### Listing All Configuration Values

To view all currently set configuration values in your `config.toml` file:

```bash
torrra config list
```

This command will display a comprehensive list of all configured settings and their current values, including general preferences and indexer-related entries.
