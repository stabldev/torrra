# Configuration

`torrra`'s behavior can be customized through a `config.toml` file, allowing you to set default paths, preferences, and other operational parameters.

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
download_path = "/home/username/Downloads"    # The default folder where torrents will be saved
remember_last_path = true                     # If set to 'true', torrra will reuse the last used download path as the default for subsequent downloads.
```

You can create or edit this file manually with a text editor.

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
torrra config set general.remember_last_path false
```

This would change the `remember_last_path` setting to `false`. Note that boolean values (`true`/`false`) should be provided as such, and strings should be enclosed in quotes if they contain spaces or special characters (though for simple paths, it might not always be necessary depending on your shell).

### Listing All Configuration Values

To view all currently set configuration values in your `config.toml` file:

```bash
torrra config list
```

This command will display a comprehensive list of all configured settings and their current values.
