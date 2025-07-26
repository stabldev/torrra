# Indexers

`torrra` relies on external torrent indexers to search for and retrieve torrent information. These indexers act as a bridge, aggregating results from various torrent sites. Currently, `torrra` integrates with popular self-hosted indexer proxies.

## Currently Supported Indexers

### Jackett

[`Jackett`](https://github.com/Jackett/Jackett) is a proxy server that translates queries from apps (like `torrra`) into tracker-specific HTTP queries, parses the HTML response, and sends results back. It supports a wide range of public and private trackers.

To use `torrra` with Jackett, you will need its URL and API key. Refer to the [Usage Guide](./usage.md) for command examples.

### Prowlarr

[`Prowlarr`](https://github.com/Prowlarr/Prowlarr) is an indexer manager and proxy for your Usenet and Torrent trackers. It integrates with your existing download clients and media management tools (like Sonarr, Radarr, etc.) and offers a unified interface to manage your indexers.

To use `torrra` with Prowlarr, you will need its URL and API key. Refer to the [Usage Guide](./usage.md) for command examples.

> **Important Note for Prowlarr Users:**
> For optimal compatibility and to ensure `torrra` can fetch magnet links correctly, please make sure the `"Prefer Magnet URL"` option is checked in your Prowlarr settings. This setting is usually found within Prowlarr's configuration for individual indexers or global settings.

## Planned Indexer Support

The development roadmap includes expanding `torrra`'s compatibility:

- Support for custom indexers (allowing users to define their own indexer integrations).
- Nyaa & anime-specific indexers (for specialized content).

## How to Use Indexers with `torrra`

When launching `torrra`, you specify which indexer to use and provide its connection details. For detailed instructions and command examples, please refer to the [Usage Guide](./usage.md).
