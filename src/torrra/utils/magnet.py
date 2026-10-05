import os
import urllib.parse
from typing import Any

import httpx
import libtorrent as lt

DEFAULT_TRACKERS: list[str] = [
    "udp://zer0day.ch:1337/announce",
    "udp://tracker.publictracker.xyz:6969/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.qu.ax:6969/announce",
    "udp://tracker.peerfect.org:6969/announce",
    "udp://tracker.opentrackr.com:6969/announce",
    "udp://tracker.ilibr.org:6969/announce",
    "udp://tracker.auctor.tv:6969/announce",
    "udp://tracker-udp.gbitt.info:80/announce",
    "udp://torrentclub.online:54123/announce",
    "udp://torrentclub.online:1984/announce",
    "udp://t.overflow.biz:6969/announce",
    "udp://retracker01-msk-virt.corbina.net:80/announce",
    "udp://mail.segso.net:6969/announce",
    "udp://leet-tracker.moe:1337/announce",
    "udp://ipv4announce.sktorrent.eu:6969/announce",
    "udp://explodie.org:6969/announce",
]


def fix_magnet_uri(uri: str) -> str:
    if not uri.startswith("magnet:"):
        return uri
    uri = uri.replace("?btih:", "?xt=urn:btih:")
    uri = uri.replace("&btih:", "&xt=urn:btih:")
    uri = uri.replace("?btmh:", "?xt=urn:btmh:")
    uri = uri.replace("&btmh:", "&xt=urn:btmh:")
    return uri


def enhance_magnet_uri(uri: str) -> str:
    uri = fix_magnet_uri(uri)
    if not uri.startswith("magnet:"):
        return uri

    existing: set[str] = set()
    if "?" in uri:
        for param in uri.split("?")[1].split("&"):
            if param.startswith("tr="):
                existing.add(urllib.parse.unquote(param[3:]))

    to_add = [tr for tr in DEFAULT_TRACKERS if tr not in existing]
    if not to_add:
        return uri

    suffix = "&".join("tr=" + urllib.parse.quote(tr, safe="") for tr in to_add)
    return f"{uri}&{suffix}" if "?" in uri else f"{uri}?{suffix}"


async def resolve_magnet_uri(input_uri: str) -> str | None:
    magnet_uri, _ = await resolve_torrent(input_uri)
    return magnet_uri


async def resolve_torrent(
    input_uri: str,
) -> tuple[str | None, Any | None]:
    if input_uri.startswith("magnet:"):
        return fix_magnet_uri(input_uri), None

    if os.path.isfile(input_uri) and input_uri.endswith(".torrent"):
        try:
            info = lt.torrent_info(input_uri)
            magnet_uri = fix_magnet_uri(lt.make_magnet_uri(info))
            return magnet_uri, info
        except (RuntimeError, OSError, ValueError):
            return None, None

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            resp = await client.get(input_uri)

        # Check for 301/302/redirect location header
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location")
            if location:
                return await resolve_torrent(location)

        content_type = resp.headers.get("content-type", "")
        # Check if content is a torrent file
        if (
            "application/x-bittorrent" in content_type
            or input_uri.endswith(".torrent")
            or resp.content.startswith(b"d8:announce")
            or resp.content.startswith(b"d10:created")
            or resp.content.startswith(b"d13:announce-list")
            or (resp.content.startswith(b"d") and b"4:info" in resp.content)
        ):
            try:
                info = lt.torrent_info(resp.content)
                magnet_uri = fix_magnet_uri(lt.make_magnet_uri(info))
                return magnet_uri, info
            except (RuntimeError, ValueError):
                pass
    except (httpx.HTTPError, OSError, RuntimeError, ValueError):
        pass

    return None, None
