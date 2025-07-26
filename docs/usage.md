# Usage

`torrra` provides a streamlined command-line interface for your torrent needs, allowing you to search for, download, and manage torrents directly from your terminal.

To get started, you need to specify an indexer (like Jackett or Prowlarr) and provide its connection details.

## Initializing with an Indexer

### Using Jackett

To use [`Jackett`](https://github.com/Jackett/Jackett) as your torrent indexer, provide its URL and API key:

```bash
torrra jackett --url http://localhost:9117 --api-key <your_jackett_api_key>
```

> Replace `<your_jackett_api_key>` with your actual Jackett API key.

### Using Prowlarr

Similarly, to use [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) as your torrent indexer:

```bash
torrra prowlarr --url http://localhost:9696 --api-key <your_prowlarr_api_key>
```

> Replace `<your_prowlarr_api_key>` with your actual Prowlarr API key.
> **Note:** When using Prowlarr, ensure the `"Prefer Magnet URL"` option is checked in your Prowlarr settings for optimal compatibility.

## Command-Line Interface (CLI)

`torrra` offers a comprehensive CLI for managing configurations and launching the application with specific indexers.

| Command            | Description                                                                                          |
| :----------------- | :--------------------------------------------------------------------------------------------------- |
| `torrra`           | Displays the help message if no subcommand is provided                                               |
| `torrra --help`    | Shows the general help message                                                                       |
| `torrra --version` | Displays the current installed version of `torrra`                                                   |
| `torrra config`    | Accesses the configuration subcommands (see below)                                                   |
| `torrra jackett`   | Initializes `torrra` using [`Jackett`](https://github.com/Jackett/Jackett) as the torrent indexer    |
| `torrra prowlarr`  | Initializes `torrra` using [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) as the torrent indexer |

### `torrra config` Subcommands

These subcommands allow you to manage `torrra`'s configuration directly from the command line.

| Subcommand                        | Description                                                      |
| :-------------------------------- | :--------------------------------------------------------------- |
| `torrra config get <key>`         | Retrieves the value associated with a specific configuration key |
| `torrra config set <key> <value>` | Sets a configuration key to a specified value                    |
| `torrra config list`              | Lists all currently set configuration values                     |

### Indexer Options

Both the `jackett` and `prowlarr` commands support the following options:

- `--url` (Required): The base URL of your Jackett or Prowlarr instance.
- `--api-key` (Required): Your API key for authentication with the indexer.
- `--no-cache`: Disables the opt-in caching feature for searches.
- `--help`: Displays specific help for the indexer command.

## Text-User Interface (TUI) Controls

Once `torrra` is running (after specifying an indexer), you'll interact with it through its intuitive Text-User Interface (TUI). Here are the primary keyboard controls for navigation and interaction:

| Key     | Action                                                                     |
| :------ | :------------------------------------------------------------------------- |
| `↑` `↓` | Navigate up and down through the list of search results                    |
| `Tab`   | Move focus to the next interactive widget (e.g., search box, results list) |
| `Enter` | Initiate the download for the currently selected torrent                   |
| `p`     | Pause the currently active download                                        |
| `r`     | Resume a previously paused download                                        |
| `q`     | Quit `torrra` and exit the application                                     |
