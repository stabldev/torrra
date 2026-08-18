# Roadmap

The development of `torrra` is an ongoing process, with a focus on enhancing its capabilities, improving user experience, and expanding its feature set. This roadmap outlines the key areas of development, including features that have been completed and those that are planned for future releases.

## Completed Features

The following features have been successfully implemented and are available in the current version of `torrra`:

- [x] **Jackett Integration:** Full support for connecting to and searching via Jackett instances.
- [x] **Prowlarr Support:** Integration with Prowlarr for managing and searching torrent indexers.
- [x] **Torrent Download UI with Pause/Resume:** A responsive Text-User Interface (TUI) for managing active torrent downloads, including the ability to pause and resume transfers.
- [x] **Config File Support:** Implementation of a `config.toml` file for persistent user preferences and settings.
- [x] **Standalone Binary & AUR Packaging:** Availability of pre-built executables for various operating systems and packaging for Arch Linux via AUR.
- [x] **Magnet Info Preview (Seeders/Leechers before download):** Ability to display crucial torrent metadata (like seeders and leechers) before initiating a download.
- [x] **Sorting & Filtering of Search Results:** Reordering results by seeders, size, title or leechers, either from a menu or by clicking a column header, plus hiding dead torrents. Starting sort and minimum seeder count are configurable.
- [x] **Keyboard Shortcuts Overlay / Help Screen:** An in-app help screen, opened with `?`, listing every keyboard shortcut grouped by where it applies.

## Planned Features

Our future development efforts will focus on introducing the following enhancements and new functionalities:

- [ ] **Sorting by Date and Category:** Extending result sorting to publish date and category, which first requires indexers to return those fields.
- [ ] **Support for Custom Indexers:** Allowing users to define and integrate their own custom torrent indexers beyond Jackett and Prowlarr.

We welcome community feedback and contributions to help shape the future of `torrra`. If you have suggestions or would like to contribute, please refer to the [Contributing Guide](contributing).
