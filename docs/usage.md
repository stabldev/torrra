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

## Direct Search

You can bypass the initial welcome screen and search for torrents directly from your command line using the `search` command:

```bash
torrra search "arch linux iso"
```

This command will immediately display the search results for the given query.

The `search` command also supports the `--no-cache` option:

```bash
torrra search "ubuntu iso" --no-cache
```

## Direct Download

You can download torrents directly from magnet URIs or .torrent files without searching using the `download` command:

```bash
torrra download "magnet:?xt=urn:btih:..."
# or torrra download "/path/to/file.torrent"
```

This command will start the download and open the downloads interface showing the new torrent.

## Selecting Files Before Downloading

By default, before a torrent starts downloading, `torrra` shows a file-selection screen that lets you choose which files to include:

1. The torrent is fetched (for magnet URIs, this waits for metadata to arrive from peers).
2. A tree of every file in the torrent appears, grouped by directory, all selected by default.
3. Toggle a file with `Space`/`Enter`, or toggle an entire directory (all of its files at once). Use **Select all** / **Select none** to bulk-change the selection.
4. Navigate with `j`/`k` and expand/collapse directories with `←`/`→`.
5. Press **Download** to start downloading only the selected files, or **Cancel** to abort.

While metadata is being fetched, nothing is written to disk: the torrent runs in metadata-only mode with all files at priority `dont_download`, so unselected files are never created. Files are only written once you confirm a selection (or press `Escape` to download everything).

Your file selection is saved with the download. If you restart `torrra`, only the files you picked are downloaded — the selection is re-applied to the torrent when it is restored, so it never falls back to downloading every file.

**Known limitation:** a deselected file that shares a piece boundary with a selected file may still have a few bytes of its data downloaded. BitTorrent pieces are hashed as a whole, and libtorrent documents that *"partial pieces may still be downloaded when setting file priorities"* (see `download_priority.hpp`). Any piece containing a selected file is downloaded in full — in libtorrent 2.1 the bytes belonging to deselected files are not written to those files (they are buffered in a temporary `.parts` file), so the deselected file is not created. This is inherent to BitTorrent piece hashing and is not a full download of the unselected file.

After the download reaches 100% you may briefly see a non-zero download speed (~10-20 seconds). This is not real downloading: it is libtorrent's rate estimate decaying after the final pieces arrived in flight. `torrra` hides it once the torrent is marked complete.

You don't have to wait for the metadata spinner or pick files at all: press **`Escape`** at any time (even while metadata is still loading) to skip selection and download every file.

The file selection screen is shown for every download entry point: search results, `torrra download <magnet_uri>`, and `torrra download <file.torrent>`.

You can skip the prompt and download everything immediately by disabling it:

```bash
torrra config set general.select_files false
```

## Managing Files After Download

Press **`f`** on a torrent in the downloads view to open the file manager. It lists every file in the torrent with its selection state, size, bytes downloaded, and completion percentage, and lets you change which files are included at any time — while a torrent is still downloading or after it has finished.

- Move through the list with `j`/`k` and toggle a file on or off with `space`.
- Press **Apply** to save your changes: the new selection is applied to the running torrent immediately and persisted, so it is re-applied if you restart `torrra` (see [Selecting Files Before Downloading](#selecting-files-before-downloading)).
- Press **Close** or `esc` to exit without changing anything.
- At least one file must remain selected; the file manager refuses to apply an empty selection.

## Command-Line Interface (CLI)

`torrra` offers a comprehensive CLI for managing configurations and launching the application with specific indexers.

| Command                                | Description                                                                                          |
| :------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| `torrra`                               | Displays the help message if no subcommand is provided                                               |
| `torrra --help`                        | Shows the general help message                                                                       |
| `torrra --version`                     | Displays the current installed version of `torrra`                                                   |
| `torrra search <query>`                | Searches for a torrent directly from the command line, bypassing the welcome screen.                 |
| `torrra download <magnet_uri_or_file>` | Downloads a torrent directly from a magnet URI or .torrent file.                                     |
| `torrra config`                        | Accesses the configuration subcommands (see below)                                                   |
| `torrra jackett`                       | Initializes `torrra` using [`Jackett`](https://github.com/Jackett/Jackett) as the torrent indexer    |
| `torrra prowlarr`                      | Initializes `torrra` using [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) as the torrent indexer |

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

| Key           | Action                                                                     |
| :------------ | :------------------------------------------------------------------------- |
| `↑` / `k`     | Navigate up through the list of search results                             |
| `↓` / `j`     | Navigate down through the list of search results                           |
| `Enter` / `l` | Initiate the download for the currently selected torrent                   |
| `ctrl+u`      | Page up in the results list                                                |
| `ctrl+d`      | Page down in the results list                                              |
| `ctrl+t`      | Open the theme switcher to change the application's appearance             |
| `G`           | Scroll to the bottom of the results list                                   |
| `gg`          | Scroll to the top of the results list (press `g` twice)                    |
| `Tab`         | Move focus to the next interactive widget (e.g., search box, results list) |
| `p`           | Pause or resume the currently selected download                       |
| `f`           | Open the file manager for the currently selected download             |
| `d`           | Delete the currently selected download from the list                  |
| `D`           | Delete the currently selected download and its data                   |
| `q`           | Quit `torrra` and exit the application                                |
