from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from torrra._types import Torrent


class SortKey(str, Enum):
    """Available sort fields, declared in the order the sort menu lists them."""

    RELEVANCE = "relevance"
    SEEDERS = "seeders"
    SIZE = "size"
    TITLE = "title"
    LEECHERS = "leechers"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


# the direction each key gets when it is selected without an explicit one,
# picked so a single keypress lands on the ordering people actually want
_DEFAULT_DESCENDING: dict[SortKey, bool] = {
    SortKey.RELEVANCE: False,
    SortKey.SEEDERS: True,
    SortKey.SIZE: True,
    SortKey.TITLE: False,
    SortKey.LEECHERS: True,
}

# indexers promise int/float for these fields but real responses don't deliver:
# jackett sends "Peers": null for some trackers, and dict.get(key, 0) keeps the
# null because the key is present. sorting a mix of None and int then raises
# TypeError, so every numeric read goes through here first.
_UNKNOWN_NUMERIC = -1.0


def coerce_numeric(value: Any, default: float = _UNKNOWN_NUMERIC) -> float:
    """Best-effort numeric read of a field an indexer may have fumbled.

    Accepts the numeric strings some indexers return, and falls back to
    ``default`` for None or anything uninterpretable.
    """
    if value is None or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    """Casefolded text for sorting, tolerating a missing value."""
    return str(value).casefold() if value is not None else ""


# relevance is intentionally absent: it means "leave the indexer's order alone"
# unknown numerics sort as -1 so they sink below a genuine 0 when descending
_SORT_FUNCS: dict[SortKey, Callable[[Torrent], Any]] = {
    SortKey.SEEDERS: lambda t: coerce_numeric(t.seeders),
    SortKey.SIZE: lambda t: coerce_numeric(t.size),
    SortKey.TITLE: lambda t: _text(t.title),
    SortKey.LEECHERS: lambda t: coerce_numeric(t.leechers),
}


def parse_sort_key(value: Any, default: SortKey = SortKey.RELEVANCE) -> SortKey:
    try:
        return SortKey(str(value).strip().lower())
    except ValueError:
        return default


def parse_sort_order(value: Any, default: bool = False) -> bool:
    """Return whether the order is descending."""
    try:
        return SortOrder(str(value).strip().lower()) is SortOrder.DESC
    except ValueError:
        return default


def parse_min_seeders(value: Any, default: int = 0) -> int:
    """Coerce a configured seeder floor, falling back on anything unusable.

    A bad value here would otherwise raise while the widget is being built,
    which crashes the app on startup and leaves no way in to fix the config.
    """
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def sort_option_label(key: SortKey) -> str:
    """Menu label showing the direction selecting this key will apply."""
    if key is SortKey.RELEVANCE:
        return "Relevance"
    return f"{key.value.title()} {'↓' if _DEFAULT_DESCENDING[key] else '↑'}"


@dataclass
class Filters:
    """Client-side narrowing applied to an already-fetched result set."""

    min_seeders: int = 0
    title_contains: str = ""
    source: str = ""

    def matches(self, torrent: Torrent) -> bool:
        # an unknown seeder count reads as 0 rather than -1, so a torrent with
        # no reported seeders survives min_seeders=0 but is hidden once the
        # user asks for seeded results only
        if coerce_numeric(torrent.seeders, 0) < self.min_seeders:
            return False
        if self.title_contains and self.title_contains.casefold() not in _text(
            torrent.title
        ):
            return False
        if not self.source:
            return True
        return self.source.casefold() == _text(torrent.source)

    @property
    def is_active(self) -> bool:
        return bool(self.min_seeders or self.title_contains or self.source)

    def clear(self) -> None:
        self.min_seeders = 0
        self.title_contains = ""
        self.source = ""


@dataclass
class ResultView:
    """Ordered, filterable view over a single search result set.

    Holds the full result list so sorting and filtering never require a re-query,
    and keeps no reference to the UI so it can be tested without a running app.
    """

    sort_key: SortKey = SortKey.RELEVANCE
    descending: bool = False
    filters: Filters = field(default_factory=Filters)
    _all: list[Torrent] = field(default_factory=list)

    def set_results(self, results: list[Torrent]) -> None:
        seen: set[str] = set()
        deduped: list[Torrent] = []

        for torrent in results:
            if torrent.magnet_uri in seen:
                continue
            seen.add(torrent.magnet_uri)
            deduped.append(torrent)

        self._all = deduped

    def set_sort(self, key: SortKey, descending: bool | None = None) -> None:
        self.sort_key = key
        self.descending = _DEFAULT_DESCENDING[key] if descending is None else descending

    def toggle_direction(self) -> None:
        self.descending = not self.descending

    def reset(self) -> None:
        """Drop filters and return to the indexer's own ordering."""
        self.filters.clear()
        self.set_sort(SortKey.RELEVANCE)

    @property
    def total(self) -> int:
        return len(self._all)

    @property
    def sort_label(self) -> str:
        if self.sort_key is SortKey.RELEVANCE and not self.descending:
            return self.sort_key.value
        return f"{self.sort_key.value} {'↓' if self.descending else '↑'}"

    def visible(self) -> list[Torrent]:
        rows = [t for t in self._all if self.filters.matches(t)]

        sort_func = _SORT_FUNCS.get(self.sort_key)
        if sort_func is None:  # relevance, i.e. whatever order the indexer returned
            if self.descending:
                rows.reverse()
            return rows

        # sorted() is stable, so equal keys keep their relevance ranking
        return sorted(rows, key=sort_func, reverse=self.descending)
