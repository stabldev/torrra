import pytest

from torrra._types import Torrent
from torrra.core.results import (
    Filters,
    ResultView,
    SortKey,
    coerce_numeric,
    parse_min_seeders,
    parse_sort_key,
    parse_sort_order,
    sort_option_label,
)


def make_torrent(
    title: str,
    size: float = 1000,
    seeders: int = 0,
    leechers: int = 0,
    source: str = "MockIndexer",
    magnet_uri: str | None = None,
) -> Torrent:
    return Torrent(
        magnet_uri=magnet_uri or f"magnet:?xt=urn:btih:{title}",
        title=title,
        size=size,
        seeders=seeders,
        leechers=leechers,
        source=source,
    )


@pytest.fixture
def sample() -> list[Torrent]:
    # deliberately ordered so relevance != any other ordering
    return [
        make_torrent("ubuntu", size=2_100_000_000, seeders=90, leechers=3),
        make_torrent("arch", size=840_499_200, seeders=523, leechers=17),
        make_torrent("tiny", size=5_000_000, seeders=1200, leechers=2),
        make_torrent("dead", size=700_000_000, seeders=0, leechers=0),
    ]


def titles(torrents: list[Torrent]) -> list[str]:
    return [t.title for t in torrents]


class TestSorting:
    def test_relevance_preserves_indexer_order(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        assert titles(view.visible()) == ["ubuntu", "arch", "tiny", "dead"]

    def test_sort_by_seeders_defaults_to_descending(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.set_sort(SortKey.SEEDERS)

        assert view.descending is True
        assert titles(view.visible()) == ["tiny", "arch", "ubuntu", "dead"]

    def test_sort_by_size_orders_numerically_not_lexically(self, sample: list[Torrent]):
        # guards the DataTable.sort() trap: "1.96 GB" < "4.77 MB" as strings
        view = ResultView()
        view.set_results(sample)
        view.set_sort(SortKey.SIZE)

        assert titles(view.visible()) == ["ubuntu", "arch", "dead", "tiny"]

    def test_sort_by_title_is_case_insensitive_and_ascending(self):
        view = ResultView()
        view.set_results(
            [make_torrent("banana"), make_torrent("Apple"), make_torrent("cherry")]
        )
        view.set_sort(SortKey.TITLE)

        assert view.descending is False
        assert titles(view.visible()) == ["Apple", "banana", "cherry"]

    def test_sort_is_stable_within_ties(self):
        # equal seeders must keep the indexer's relevance ranking
        view = ResultView()
        view.set_results(
            [
                make_torrent("first", seeders=10),
                make_torrent("second", seeders=10),
                make_torrent("third", seeders=10),
            ]
        )
        view.set_sort(SortKey.SEEDERS)

        assert titles(view.visible()) == ["first", "second", "third"]

    def test_toggle_direction_flips_order(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.set_sort(SortKey.SEEDERS)
        view.toggle_direction()

        assert titles(view.visible()) == ["dead", "ubuntu", "arch", "tiny"]

    def test_descending_relevance_reverses_indexer_order(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.toggle_direction()

        assert titles(view.visible()) == ["dead", "tiny", "arch", "ubuntu"]

    def test_visible_does_not_mutate_stored_results(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.toggle_direction()
        view.visible()  # reverses a copy, not the backing list

        view.set_sort(SortKey.RELEVANCE)
        assert titles(view.visible()) == ["ubuntu", "arch", "tiny", "dead"]

    def test_set_sort_applies_each_keys_natural_direction(self):
        view = ResultView()

        # the menu advertises these directions, so selecting must match
        view.set_sort(SortKey.SEEDERS)
        assert view.descending is True
        view.set_sort(SortKey.TITLE)
        assert view.descending is False
        view.set_sort(SortKey.RELEVANCE)
        assert view.descending is False

    def test_explicit_direction_overrides_the_default(self):
        view = ResultView()
        view.set_sort(SortKey.SEEDERS, descending=False)
        assert view.descending is False


class TestFiltering:
    def test_min_seeders_excludes_dead_torrents(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.filters.min_seeders = 1

        assert "dead" not in titles(view.visible())
        assert len(view.visible()) == 3

    def test_min_seeders_is_inclusive_at_the_boundary(self):
        view = ResultView()
        view.set_results([make_torrent("exact", seeders=5)])
        view.filters.min_seeders = 5

        assert len(view.visible()) == 1

    def test_title_contains_is_case_insensitive(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.filters.title_contains = "UBUNT"

        assert titles(view.visible()) == ["ubuntu"]

    def test_source_filter_matches_exactly(self):
        view = ResultView()
        view.set_results(
            [make_torrent("a", source="Nyaa"), make_torrent("b", source="RARBG")]
        )
        view.filters.source = "nyaa"

        assert titles(view.visible()) == ["a"]

    def test_total_reports_unfiltered_count(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.filters.min_seeders = 1

        assert view.total == 4
        assert len(view.visible()) == 3

    def test_filters_and_sort_compose(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.set_sort(SortKey.SEEDERS)
        view.filters.min_seeders = 100

        assert titles(view.visible()) == ["tiny", "arch"]

    def test_all_filtered_out_yields_empty(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.filters.min_seeders = 10_000

        assert view.visible() == []
        assert view.total == 4

    def test_is_active_reflects_state(self):
        filters = Filters()
        assert filters.is_active is False

        filters.min_seeders = 1
        assert filters.is_active is True

        filters.clear()
        assert filters.is_active is False

    def test_reset_restores_relevance_and_clears_filters(self, sample: list[Torrent]):
        view = ResultView()
        view.set_results(sample)
        view.set_sort(SortKey.SEEDERS)
        view.filters.min_seeders = 100
        view.reset()

        assert view.sort_key is SortKey.RELEVANCE
        assert view.filters.is_active is False
        assert titles(view.visible()) == ["ubuntu", "arch", "tiny", "dead"]


class TestDeduplication:
    def test_duplicate_magnet_uris_are_dropped(self):
        view = ResultView()
        view.set_results(
            [
                make_torrent("a", magnet_uri="magnet:dup"),
                make_torrent("b", magnet_uri="magnet:dup"),
                make_torrent("c", magnet_uri="magnet:c"),
            ]
        )

        # first occurrence wins, and numbering stays contiguous
        assert titles(view.visible()) == ["a", "c"]
        assert view.total == 2

    def test_empty_results(self):
        view = ResultView()
        view.set_results([])

        assert view.visible() == []
        assert view.total == 0


class TestConfigParsing:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("seeders", SortKey.SEEDERS),
            ("  SIZE  ", SortKey.SIZE),
            ("Title", SortKey.TITLE),
            ("relevance", SortKey.RELEVANCE),
            ("nonsense", SortKey.RELEVANCE),
            (None, SortKey.RELEVANCE),
            (42, SortKey.RELEVANCE),
        ],
    )
    def test_parse_sort_key(self, raw: object, expected: SortKey):
        assert parse_sort_key(raw) is expected

    @pytest.mark.parametrize(
        "raw,expected",
        [("desc", True), ("DESC", True), ("asc", False), ("bogus", False)],
    )
    def test_parse_sort_order(self, raw: object, expected: bool):
        assert parse_sort_order(raw) is expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (5, 5),
            ("5", 5),
            (0, 0),
            (-3, 0),  # a negative floor is meaningless, clamp it
            ("abc", 0),  # config.set stores unparseable values as plain strings
            (None, 0),
            ("", 0),
        ],
    )
    def test_parse_min_seeders_never_raises(self, raw: object, expected: int):
        assert parse_min_seeders(raw) == expected


class TestSortLabel:
    def test_plain_relevance_has_no_arrow(self):
        assert ResultView().sort_label == "relevance"

    def test_directional_keys_show_an_arrow(self):
        view = ResultView()
        view.set_sort(SortKey.SEEDERS)
        assert view.sort_label == "seeders ↓"

        view.toggle_direction()
        assert view.sort_label == "seeders ↑"


class TestSortOptionLabel:
    def test_relevance_has_no_direction(self):
        assert sort_option_label(SortKey.RELEVANCE) == "Relevance"

    @pytest.mark.parametrize(
        "key,expected",
        [
            (SortKey.SEEDERS, "Seeders \u2193"),
            (SortKey.SIZE, "Size \u2193"),
            (SortKey.LEECHERS, "Leechers \u2193"),
            (SortKey.TITLE, "Title \u2191"),
        ],
    )
    def test_label_arrow_matches_applied_direction(self, key: SortKey, expected: str):
        assert sort_option_label(key) == expected

        # the arrow shown in the menu must be what selecting actually does
        view = ResultView()
        view.set_sort(key)
        assert view.descending is (expected.endswith("\u2193"))

    def test_every_key_has_a_label(self):
        assert all(sort_option_label(k) for k in SortKey)


class TestMalformedIndexerFields:
    """Real indexers violate the int/float annotations on Torrent.

    Jackett sends ``"Peers": null`` for some trackers, and because the key is
    present ``dict.get("Peers", 0)`` hands back the null. Sorting a mix of
    None and int then raised TypeError and took the whole app down, so every
    numeric read is coerced before it is compared.
    """

    @staticmethod
    def _mixed() -> list[Torrent]:
        # mirrors a real jackett page: mostly ints, a few nulls, one numeric
        # string, and ties that must keep their relevance order
        return [
            make_torrent("a", seeders=10, leechers=5),
            make_torrent("b", seeders=3, leechers=None),  # pyright: ignore
            make_torrent("c", seeders=7, leechers=0),
            make_torrent("d", seeders=1, leechers="12"),  # pyright: ignore
            make_torrent("e", seeders=None, leechers=None),  # pyright: ignore
            make_torrent("f", seeders=4, leechers=5),
        ]

    @pytest.mark.parametrize(
        "key", [SortKey.LEECHERS, SortKey.SEEDERS, SortKey.SIZE, SortKey.TITLE]
    )
    def test_sorting_never_raises_on_missing_values(self, key: SortKey):
        view = ResultView()
        view.set_results(self._mixed())
        view.set_sort(key)

        assert len(view.visible()) == 6
        view.toggle_direction()
        assert len(view.visible()) == 6

    def test_unknown_leechers_sort_below_a_real_zero(self):
        view = ResultView()
        view.set_results(self._mixed())
        view.set_sort(SortKey.LEECHERS)  # descending by default

        titles = [t.title for t in view.visible()]
        # "12" parses as a number and leads; the two unknowns land under
        # torrent "c", which genuinely reports zero leechers
        assert titles == ["d", "a", "f", "c", "b", "e"]

    def test_unknown_seeders_survive_an_inactive_filter(self):
        """min_seeders=0 must not hide a torrent whose count is unknown."""
        view = ResultView()
        view.set_results(self._mixed())

        assert view.filters.min_seeders == 0
        assert len(view.visible()) == 6

    def test_unknown_seeders_are_hidden_once_seeded_only_is_on(self):
        view = ResultView()
        view.set_results(self._mixed())
        view.filters.min_seeders = 1

        # "e" reports no seeders at all, so it cannot be claimed as seeded
        assert [t.title for t in view.visible()] == ["a", "b", "c", "d", "f"]

    def test_missing_title_does_not_break_sorting_or_filtering(self):
        view = ResultView()
        view.set_results(
            [
                make_torrent("beta"),
                make_torrent(None),  # pyright: ignore
                make_torrent("Alpha"),
            ]
        )
        view.set_sort(SortKey.TITLE)
        assert len(view.visible()) == 3

        view.filters.title_contains = "alpha"
        assert [t.title for t in view.visible()] == ["Alpha"]


class TestCoerceNumeric:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (5, 5.0),
            (3.9, 3.9),
            (0, 0.0),
            ("7", 7.0),  # some indexers quote their numbers
            (None, -1.0),  # jackett's "Peers": null
            ("", -1.0),
            ("abc", -1.0),
            ([], -1.0),
            (True, -1.0),  # a bool is not a real count
        ],
    )
    def test_coercion_never_raises(self, raw: object, expected: float):
        assert coerce_numeric(raw) == expected

    def test_default_is_overridable(self):
        # filtering treats an unknown count as 0 so it is not hidden by
        # min_seeders=0, while sorting uses -1 so it sinks to the bottom
        assert coerce_numeric(None, 0) == 0
        assert coerce_numeric(None) == -1.0
