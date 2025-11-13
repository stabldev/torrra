import os
import tempfile
from contextlib import suppress

import httpx
import libtorrent as lt


async def resolve_magnet_uri(input_uri: str) -> str | None:
    if input_uri.startswith("magnet:"):
        return input_uri

    try:
        # some torrent doesnt have magnet uri, instead a uri to .torrent file
        # send request to that uri and parse content
        async with httpx.AsyncClient(follow_redirects=False) as client:
            resp = await client.get(input_uri)

        # get magnet uri from location header
        if resp.status_code in (301, 302):
            return resp.headers.get("location")

        # if its a .torrent file
        content_type = resp.headers.get("content-type", "")
        if "application/x-bittorrent" in content_type or input_uri.endswith(".torrent"):
            with tempfile.NamedTemporaryFile(suffix=".torrent", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            try:
                info = lt.torrent_info(tmp_path)
                return lt.make_magnet_uri(info)
            finally:
                # delete file silently
                with suppress(Exception):
                    os.remove(tmp_path)
    except Exception as e:
        print(f"an unexpected error occurred: {e}")
    return None
