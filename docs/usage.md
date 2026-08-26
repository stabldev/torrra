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

## Welcome Screen

Running `torrra` with no arguments opens the welcome screen, where you type a search query. You can skip searching and go straight to the Downloads view by pressing `ctrl+d`.

## Direct Download

You can download torrents directly from magnet URIs, URLs, or local `.torrent`
files without searching using the `download` command:

```bash
torrra download "magnet:?xt=urn:btih:..."
# or torrra download "/path/to/file.torrent"
# optionally prefill a per-torrent destination
torrra download "https://example.com/file.torrent" --save-path /downloads/linux
```

The file-selection screen lets you choose files and an optional **Save to**
directory before the download starts. It initially shows
`general.download_path`; leave it unchanged or clear it to keep using the global
fallback. A different selected directory is saved with the torrent and reused
after restarting Torrra.

## Command-Line Interface (CLI)

`torrra` offers a comprehensive CLI for managing configurations and launching the application with specific indexers.

| Command                                | Description                                                                                          |
| :------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| `torrra`                               | Displays the help message if no subcommand is provided                                               |
| `torrra --help`                        | Shows the general help message                                                                       |
| `torrra download <uri/file>`           | Directly downloads a torrent with optional `--save-path`                                            |
| `torrra search <query>`                | Searches for torrents directly from the CLI                                                          |
| `torrra downloads`                     | Directly opens the downloads view                                                                    |
| `torrra config`                        | Manages `torrra` configuration                                                                       |
| `torrra jackett`                       | Initializes `torrra` using [`Jackett`](https://github.com/Jackett/Jackett) as the torrent indexer    |
| `torrra prowlarr`                      | Initializes `torrra` using [`Prowlarr`](https://github.com/Prowlarr/Prowlarr) as the torrent indexer |

### `torrra config` Subcommands

These subcommands allow you to manage `torrra`'s configuration directly from the command line.

| Subcommand                        | Description                                                      |
| :-------------------------------- | :--------------------------------------------------------------- |
| `torrra config get <key>`         | Retrieves the value associated with a specific configuration key |
| `torrra config set <key> <value>` | Sets a configuration key to a specified value                    |
| `torrra config list`              | Lists all currently set configuration values                     |
| `torrra config edit`              | Opens the configuration file in the default editor               |

### Indexer Options

Both the `jackett` and `prowlarr` commands support the following options:

- `--url` (Required): The base URL of your Jackett or Prowlarr instance.
- `--api-key` (Required): Your API key for authentication with the indexer.
- `--no-cache`: Disables the opt-in caching feature for searches.
- `--help`: Displays specific help for the indexer command.

## Text-User Interface (TUI) Controls

Once `torrra` is running (after specifying an indexer), you'll interact with it through its Text-User Interface (TUI).

The TUI has two views, **Search** and **Downloads**, which you switch between using the sidebar. Some keys work everywhere, and some only apply to one view.

### Anywhere in the app

| Key      | Action                                                       |
| :------- | :----------------------------------------------------------- |
| `Tab`    | Move focus between the search box, the sidebar and the list  |
| `ctrl+t` | Open the theme switcher to change the application's appearance |
| `t`      | Toggle turtle mode — cap all traffic at your configured global speed limits (set them in `config.toml` under `[speed_limit]`, e.g. `torrra config set speed_limit.download_limit 2M`) |
| `?`      | Show all keyboard shortcuts                                  |
| `ctrl+q` | Quit `torrra`                                                |

### Moving around a list

These work in both the search results and the downloads list.

| Key       | Action                                       |
| :-------- | :------------------------------------------- |
| `↑` / `k` | Move up one row                              |
| `↓` / `j` | Move down one row                            |
| `ctrl+u`  | Page up                                      |
| `ctrl+d`  | Page down                                    |
| `gg`      | Jump to the top (press `g` twice, quickly)   |
| `G`       | Jump to the bottom                           |

### Search results

| Key           | Action                                                                       |
| :------------ | :--------------------------------------------------------------------------- |
| `Enter` / `l` | Open the details panel for the highlighted torrent                           |
| `Enter`       | Start the download (while the details panel is focused)                      |
| `Esc`         | Close the details panel                                                      |
| `s`           | Open the sort menu to pick a field: relevance, seeders, size, title, leechers |
| `S`           | Reverse the current sort direction                                           |
| `f`           | Toggle hiding results that have 0 seeders                                    |
| `x`           | Reset sorting and filters back to your configured defaults                   |

### Downloads

| Key           | Action                                                       |
| :------------ | :----------------------------------------------------------- |
| `Enter` / `l` | Show details and progress for the highlighted download       |
| `p`           | Pause or resume the selected download (the same key toggles) |
| `f`           | Open the file selection modal to choose files to download    |
| `o` / `s`     | Open torrent options (speed limits, max ratio, seed time, sequential download) |
| `d`           | Remove the selected torrent, keeping any downloaded files    |
| `D`           | Remove the selected torrent **and** delete its files         |

While a download's details panel is open, per-torrent limits, current seed ratio,
and sequential status (`[Seq]`) are displayed.

### File selection

Files are shown in a collapsible folder tree. Folders are expanded by default; use the arrow keys to navigate, `←`/`→` to collapse/expand a folder, and `Space` to toggle the highlighted file — or a whole folder subtree. The **Save to** field accepts an absolute path; leave it blank to use the configured global default.

| Key            | Action                                                      |
| :------------- | :---------------------------------------------------------- |
| `Space`        | Toggle selection of the highlighted file / folder subtree   |
| `←` / `→`      | Collapse / expand the highlighted folder                    |
| `j` / `k`      | Move the selection cursor up / down                         |
| `a`            | Select all files                                            |
| `n`            | Select no files (clear selection)                           |
| `i`            | Invert selection                                            |
| `Enter`        | Confirm selection and start download                        |
| `d`            | Download all files immediately (skip metadata fetching wait) |
| `Esc`          | Cancel file selection                                       |

### Discovering Shortcuts In the App

You don't need to keep this page open to remember the keys. Press `?` at any time to
open a help screen listing every shortcut, grouped by the same sections used above,
since most keys only do something in one of the two views.

Press `?` again, or `Esc`, to close it. On a short terminal the list won't fit all at
once, so the panel scrolls with the same keys as the rest of the app (`j`/`k`,
`ctrl+d`/`ctrl+u`, `gg`/`G`).

Like the sort and filter keys, `?` steps aside while you're typing a query in the search box, so
it never interferes with typing — though when the search box is empty, pressing `?` opens help directly.

### Sorting and Filtering Results

Indexers return results in their own order, which is usually a relevance guess and often buries the copies that will actually download quickly. Sorting and filtering let you reorder and narrow what you already have, without querying your indexer again — `torrra` keeps the full result set in memory, so it's instant.

#### A first walkthrough

Say you search for `ubuntu iso` and get 40 results in no obvious order.

1. Press `Tab` (or `↓`) to move focus out of the search box and into the results list. **This step matters** — see the note below.
2. Press `f`. Every result with 0 seeders disappears. Those are dead torrents that would never finish downloading, and real indexers return a lot of them.
3. Press `s`, then `j`/`k` to highlight **seeders**, then `Enter`. The results reorder with the healthiest torrents at the top, since more seeders generally means a faster download.
4. The border above the list now reads something like `results (12/40) · seeders ↓` — 12 of the 40 results are shown, sorted by seeders, highest first.
5. Press `Enter` on the top result to open its details, then `Enter` again to start downloading.

That's the common path: **`f` then `s`** gets you from a raw result dump to the best few candidates in two keystrokes.

You don't have to memorise any of this. The bottom border of the results list always shows a reminder: `s sort · S order · f seeded · x reset`.

> **If pressing `s` types the letter "s" instead**, your focus is still in the search box. These keys only act as shortcuts when the results list has focus — press `Tab` first. This is deliberate, so the shortcuts can never interfere with typing a query.

#### The rest of the controls

- Press `S` to reverse the current direction. Useful for finding the *smallest* file rather than the largest.
- Press `x` to reset sorting and filters back to your configured defaults. Out of the box that's the indexer's own ranking with nothing hidden; if you've set `default_sort` or `min_seeders`, `x` returns you to those. To reach the indexer's raw ranking regardless, click the `#` header.
- In the sort menu, `Esc` closes without changing anything, and the highlight starts on whichever field is already active, so `Enter` is never a surprise.

Each field starts in the direction you'd usually want, shown next to its name in the menu: `seeders`, `size` and `leechers` sort high-to-low (`↓`), while `title` sorts A-Z (`↑`).

You can also **click a column header** to sort by it, if your terminal has mouse support. Clicking a new column applies that column's default direction, clicking the column that's already active reverses it, and clicking `#` returns to the indexer's own ranking.

#### Details worth knowing

Sorting is stable, so results that tie on the sort field keep their original relevance ranking rather than jumping around.

Your choices persist across searches for the rest of the session — sort once, and the next search comes back already sorted. To make them permanent, set `default_sort`, `default_sort_order` and `min_seeders` in your [configuration](configuration.md). `default_sort_order` defaults to `auto`, which gives each field its natural direction, so setting `default_sort = "title"` loads A-Z rather than Z-A.

Sorting and filtering are independent. Changing the sort keeps your filter, and vice versa.
