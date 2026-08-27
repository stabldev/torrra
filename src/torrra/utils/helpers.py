from contextlib import suppress
from itertools import pairwise


def human_readable_size(size_bytes: float, short: bool = False) -> str:
    if not short:
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    # short version
    if size_bytes < 1024:
        return f"{int(size_bytes)} B"

    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            number = (
                f"{size_bytes:.1f}".rstrip("0").rstrip(".")
                if size_bytes < 10
                else str(int(size_bytes))
            )
            return f"{number} {unit}"
    size_bytes /= 1024.0
    return f"{int(size_bytes)} PB"


def human_readable_eta(seconds: float | None, is_seeding: bool = False) -> str:
    if is_seeding or seconds is None or seconds < 0 or seconds == float("inf"):
        return "∞"

    total_seconds = int(seconds)
    if total_seconds == 0:
        return "0s"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    units = [(days, "d"), (hours, "h"), (minutes, "m"), (secs, "s")]
    for (val, unit), (sub_val, sub_unit) in pairwise(units):
        if val > 0:
            return f"{val}{unit} {sub_val}{sub_unit}" if sub_val > 0 else f"{val}{unit}"
    return f"{secs}s"


def parse_speed_limit(text: str) -> int:
    """Parse a human speed limit into bytes/second.

    Returns ``-1`` for unlimited (empty, ``0``, ``unlimited`` or ``off``).
    Accepts suffixes ``K``/``KB`` (1024), ``M``/``MB`` (1024**2) and
    ``G``/``GB`` (1024**3), optionally followed by ``/s``. Raises
    ``ValueError`` on invalid input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned.endswith("/s"):
        cleaned = cleaned[:-2].strip()
    if cleaned in ("", "0", "unlimited", "off", "none"):
        return -1

    units = {
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "mib": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "gib": 1024**3,
    }

    for suffix, multiplier in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if cleaned.endswith(suffix):
            number_part = cleaned[: -len(suffix)].strip()
            value = float(number_part) * multiplier
            if value < 0:
                raise ValueError("speed limit must not be negative")
            return int(value)

    # bare number => bytes/second
    value = float(cleaned)
    if value < 0:
        raise ValueError("speed limit must not be negative")
    return int(value)


def coerce_speed_limit(value: object) -> int:
    """Coerce a stored speed-limit config value to bytes/second.

    Ints pass through (normalized to >= 0); strings (e.g. ``"10 KB/s"``, ``"2M"``
    in config.toml) are parsed, and anything unparsable or unlimited (``"0"``,
    ``"unlimited"``) falls back to ``0`` instead of crashing readers.
    """
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, parse_speed_limit(str(value)))
    except ValueError:
        return 0


def parse_ratio_limit(text: str) -> float:
    """Parse a seed ratio limit into a float.

    Returns ``-1.0`` for unlimited (empty, ``0``, ``0.0``, ``unlimited``, ``off``, or ``none``).
    Raises ``ValueError`` on invalid or negative input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned in ("", "0", "0.0", "unlimited", "off", "none"):
        return -1.0
    try:
        val = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"invalid ratio limit: '{text}'") from exc
    if val < 0:
        raise ValueError("ratio limit must not be negative")
    if val == 0:
        return -1.0
    return val


def format_ratio_limit(value: float | None) -> str:
    """Format a ratio limit for prefilling input forms."""
    if value is None or value <= 0:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def coerce_ratio_limit(value: object) -> float:
    """Coerce a ratio limit config or db value to float >= 0.0."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    try:
        parsed = parse_ratio_limit(str(value))
        return max(0.0, parsed)
    except ValueError:
        return 0.0


def parse_seeding_time(text: str) -> int:
    """Parse a seeding duration limit into minutes.

    Returns ``-1`` for unlimited (empty, ``0``, ``unlimited``, ``off``, or ``none``).
    Accepts suffixes ``d``/``day``/``days``, ``h``/``hr``/``hrs``/``hours``,
    ``m``/``min``/``mins``/``minutes``, or bare minutes.
    Raises ``ValueError`` on invalid or negative input.
    """
    cleaned = (text or "").strip().lower()
    if cleaned in ("", "0", "unlimited", "off", "none"):
        return -1

    units = [
        (("days", "day", "d"), 1440),
        (("hours", "hour", "hrs", "hr", "h"), 60),
        (("minutes", "minute", "mins", "min", "m"), 1),
    ]

    for suffixes, multiplier in units:
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                number_part = cleaned[: -len(suffix)].strip()
                try:
                    val = float(number_part) * multiplier
                except ValueError as exc:
                    raise ValueError(f"invalid seeding time: '{text}'") from exc
                if val < 0:
                    raise ValueError("seeding time must not be negative")
                return int(val)

    try:
        val = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"invalid seeding time: '{text}'") from exc
    if val < 0:
        raise ValueError("seeding time must not be negative")
    return int(val)


def format_seeding_time(minutes: int | None) -> str:
    """Format seeding duration in minutes for prefilling input forms."""
    if minutes is None or minutes <= 0:
        return ""
    if minutes % 1440 == 0:
        return f"{minutes // 1440}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def coerce_seeding_time(value: object) -> int:
    """Coerce a seeding time config or db value to integer minutes >= 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    try:
        parsed = parse_seeding_time(str(value))
        return max(0, parsed)
    except ValueError:
        return 0


def lazy_import(dotted_path: str):
    import importlib

    try:
        module_path, obj_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, obj_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"failed to import: {dotted_path}\n{e}")


def get_tomllib():
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # Python <3.11
        import tomli as tomllib  # type: ignore

    return tomllib


AZUREUS_CLIENTS: dict[str, str] = {
    "7T": "aTorrent",
    "AB": "AnyEvent::BitTorrent",
    "AG": "Ares",
    "A~": "Ares",
    "AR": "Arctic",
    "AT": "Artemis",
    "AV": "Avicora",
    "AZ": "Vuze",
    "BB": "BitBuddy",
    "BC": "BitComet",
    "BE": "Baretorrent",
    "BF": "BitFlu",
    "BG": "BTG",
    "BI": "BiglyBT",
    "BL": "BitLord",
    "BP": "BitTorrent Pro",
    "BR": "BitRocket",
    "BS": "BTSlave",
    "BT": "BitTorrent",
    "BW": "BitWombat",
    "BX": "BittorrentX",
    "CD": "Enhanced CTorrent",
    "CT": "CTorrent",
    "DE": "Deluge",
    "DP": "DirectoryPlate",
    "EB": "EBit",
    "FC": "FileCroc",
    "FD": "Free Download Manager",
    "FG": "FlashGet",
    "FL": "Folx",
    "FT": "FoxTorrent",
    "FW": "FrostWire",
    "FX": "Freebox BitTorrent",
    "GR": "GrabBit",
    "GS": "GSTorrent",
    "HL": "Halite",
    "HN": "Hydranode",
    "KG": "KGet",
    "KT": "KTorrent",
    "LH": "LH-ABC",
    "LK": "Linktorrent",
    "LP": "Lphant",
    "LT": "libtorrent",
    "lt": "libtorrent",
    "LW": "LimeWire",
    "MG": "MediaGet",
    "MK": "Meerkat",
    "ML": "MLDonkey",
    "MO": "MonoTorrent",
    "MP": "MooPolice",
    "MR": "Miro",
    "MT": "MoonlightTorrent",
    "NE": "NetExtensions",
    "NX": "Net Transport",
    "OS": "OneSwarm",
    "OT": "OmegaTorrent",
    "PD": "Pando",
    "PI": "PicoTorrent",
    "QD": "QQDownload",
    "qB": "qBittorrent",
    "QT": "QtTorrent",
    "RT": "Retriever",
    "SB": "Swiftbit",
    "SD": "Xunlei",
    "SN": "Sharenet",
    "SS": "SwarmScope",
    "ST": "SymTorrent",
    "SZ": "Shareaza",
    "TB": "Torch",
    "TD": "TidTor",
    "TL": "Tribler",
    "TN": "TorrentDotNET",
    "TO": "Torrra",
    "TR": "Transmission",
    "TS": "Tixati",
    "TT": "TuoTu",
    "UL": "uLeecher!",
    "UM": "µTorrent Mac",
    "UT": "µTorrent",
    "VG": "Vagaa",
    "WD": "WebTorrent Desktop",
    "WT": "BitLet",
    "WW": "WebTorrent",
    "WY": "FireTorrent",
    "XF": "Xfplay",
    "XL": "Xunlei",
    "XS": "XSwifter",
    "XT": "XanTorrent",
    "XX": "Xtorrent",
    "ZT": "ZipTorrent",
}


def parse_peer_client(client_raw: object, pid_raw: object) -> str:
    """Identify a peer's BitTorrent client.

    Prefers the BEP 10 extended handshake client string if present. Otherwise,
    parses the 20-byte Peer ID (BEP 20 convention) sent in the initial handshake.
    """
    if client_raw:
        if isinstance(client_raw, bytes):
            decoded = client_raw.decode("utf-8", errors="replace").strip()
        else:
            decoded = str(client_raw).strip()
        if decoded:
            return decoded

    if not pid_raw:
        return "Unknown"

    pid = b""
    to_bytes_fn = getattr(pid_raw, "to_bytes", None)
    if callable(to_bytes_fn):
        with suppress(Exception):
            res = to_bytes_fn()
            if isinstance(res, (bytes, bytearray)):
                pid = bytes(res)
    elif isinstance(pid_raw, (bytes, bytearray)):
        pid = bytes(pid_raw)

    if not pid or len(pid) < 8 or all(b == 0 for b in pid):
        return "Unknown"

    # 1. Azureus style: -XX1234-
    if pid[0:1] == b"-" and pid[7:8] == b"-":
        code = pid[1:3].decode("ascii", errors="ignore")
        client_name = AZUREUS_CLIENTS.get(code, code)
        v_chars: list[str] = []
        for b in pid[3:7]:
            if 48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122:
                v_chars.append(chr(b))
            else:
                break
        if v_chars:
            res = ".".join(v_chars)
            while res.endswith(".0") and res.count(".") > 1:
                res = res[:-2]
            return f"{client_name} {res}".strip()
        return client_name

    # 2. Mainline style: M3-4-2--...
    if len(pid) >= 7 and pid[0:1] == b"M" and pid[2:3] == b"-" and pid[4:5] == b"-":
        try:
            v = f"{chr(pid[1])}.{chr(pid[3])}.{chr(pid[5])}"
            return f"BitTorrent {v}"
        except ValueError:
            pass

    # 3. BitComet: exbc\x01\x02
    if len(pid) >= 6 and pid[:4] == b"exbc":
        return f"BitComet {pid[4]}.{pid[5]:02d}"

    # 4. Free Download Manager: FMD
    if pid[:3] == b"FMD":
        return "Free Download Manager"

    return "Unknown"
