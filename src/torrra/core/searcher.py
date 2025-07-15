def search_torrents(query):
    return [
        {"name": f"{query} 1080p BluRay", "size": "1.4 GB", "seeders": 1400},
        {"name": f"{query} 720p x265", "size": "900 MB", "seeders": 800},
        {"name": f"{query} DVDRip", "size": "700 MB", "seeders": 500},
    ]
