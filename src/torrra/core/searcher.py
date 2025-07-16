def search_torrents(query):
    return [
        {
            "name": f"{query} 1080p BluRay",
            "size": "1.4 GB",
            "seed": 1400,
            "leech": 2100,
            "source": "YTS",
        },
        {
            "name": f"{query} 720p x265",
            "size": "900 MB",
            "seed": 800,
            "leech": 1300,
            "source": "MagnetDL",
        },
        {
            "name": f"{query} DVDRip",
            "size": "700 MB",
            "seed": 500,
            "leech": 900,
            "source": "YTS",
        },
    ]
