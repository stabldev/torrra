from typing import cast
from unittest.mock import MagicMock

import pytest
from textual.coordinate import Coordinate
from textual.geometry import Offset, Region
from textual.pilot import Pilot
from textual.widgets import DataTable, ListView, Static
from textual.widgets.data_table import ColumnKey

from torrra._types import Indexer, Torrent
from torrra.app import TorrraApp
from torrra.core.config import Config
from torrra.core.results import SortKey
from torrra.screens.home import HomeScreen
from torrra.screens.sort_selector import SortSelectorScreen
from torrra.widgets.search import SearchContent


@pytest.fixture
def app():
    # start app on SearchScreen
    # by providing a default search_query
    return TorrraApp(
        indexer=Indexer(
            name="jackett", url="http://mock.indexer.url", api_key="mock_api_key"
        ),
        use_cache=False,
        search_query="arch linux iso",
    )


async def test_home_screen_search(app: TorrraApp, mock_indexer: MagicMock):
    mock_indexer.search.return_value = [
        Torrent(
            magnet_uri="magnet:?xt=urn:btih:mock",
            title="Arch Linux ISO (Mock)",
            size=840499200,
            seeders=523,
            leechers=17,
            source="MockIndexer",
        )
    ]

    async with app.run_test():
        assert isinstance(app.screen, HomeScreen)

        table = cast(
            DataTable[str], app.screen.query_one("SearchContent DataTable", DataTable)
        )
        # table should have results
        assert not table.has_class("hidden")

        # verify table has the correct number of rows and content
        assert table.row_count == len(mock_indexer.search.return_value)
        assert table.get_cell_at(Coordinate(0, 1)) == "Arch Linux ISO (Mock)"


async def test_home_screen_search_no_results(app: TorrraApp, mock_indexer: MagicMock):
    # ensure result is empty []
    mock_indexer.search.return_value = []

    async with app.run_test():
        assert isinstance(app.screen, HomeScreen)

        loader_status = app.screen.query_one("#loader Static", Static)
        table = app.screen.query_one("SearchContent DataTable")

        assert "Nothing Found" in str(loader_status.content)
        assert table.has_class("hidden")


# indexer order is deliberately NOT sorted by any column, so a passing
# ordering assertion can only come from the sort actually being applied
SORT_FIXTURE = [
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:ubuntu",
        title="Ubuntu 24.04",
        size=5_000_000_000,
        seeders=100,
        leechers=10,
        source="MockIndexer",
    ),
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:arch",
        title="Arch Linux ISO",
        size=840_499_200,
        seeders=523,
        leechers=17,
        source="MockIndexer",
    ),
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:debian",
        title="Debian 12 (no seeds)",
        size=3_000_000_000,
        seeders=0,
        leechers=1,
        source="MockIndexer",
    ),
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:fedora",
        title="Fedora 40",
        size=2_000_000_000,
        seeders=250,
        leechers=5,
        source="MockIndexer",
    ),
]


def _titles(table: DataTable[str]) -> list[str]:
    return [table.get_cell_at(Coordinate(r, 1)) for r in range(table.row_count)]


def _numbers(table: DataTable[str]) -> list[str]:
    return [table.get_cell_at(Coordinate(r, 0)) for r in range(table.row_count)]


def _table_of(app: TorrraApp) -> DataTable[str]:
    return cast(
        DataTable[str], app.screen.query_one("SearchContent DataTable", DataTable)
    )


async def _choose_sort(pilot: Pilot[None], app: TorrraApp, key: SortKey) -> None:
    """Open the sort menu and pick a field, the way a user would."""
    await pilot.press("s")
    await pilot.pause()

    screen = app.screen
    assert isinstance(screen, SortSelectorScreen), "s should open the sort menu"

    screen.query_one(ListView).index = list(SortKey).index(key)
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


@pytest.fixture
def sort_app(app: TorrraApp, mock_indexer: MagicMock, mock_config: Config):
    # mock_config pins the sort/filter defaults so these assertions don't
    # depend on the developer's real config.toml
    mock_indexer.search.return_value = list(SORT_FIXTURE)
    return app


async def test_results_default_to_indexer_relevance_order(sort_app: TorrraApp):
    async with sort_app.run_test():
        table = _table_of(sort_app)
        assert _titles(table) == [t.title for t in SORT_FIXTURE]


async def test_sort_menu_orders_by_seeders_descending(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SEEDERS)

        table = _table_of(sort_app)
        assert _titles(table) == [
            "Arch Linux ISO",  # 523
            "Fedora 40",  # 250
            "Ubuntu 24.04",  # 100
            "Debian 12 (no seeds)",  # 0
        ]


async def test_toggle_sort_order_reverses_direction(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SEEDERS)
        await pilot.press("S")
        await pilot.pause()

        table = _table_of(sort_app)
        assert _titles(table) == [
            "Debian 12 (no seeds)",  # 0
            "Ubuntu 24.04",  # 100
            "Fedora 40",  # 250
            "Arch Linux ISO",  # 523
        ]


async def test_sort_by_size_is_numeric_not_lexical(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SIZE)

        table = _table_of(sort_app)
        # lexical ordering of the *rendered* sizes would put "840.49 MB" first
        assert _titles(table) == [
            "Ubuntu 24.04",  # 5.0 GB
            "Debian 12 (no seeds)",  # 3.0 GB
            "Fedora 40",  # 2.0 GB
            "Arch Linux ISO",  # 840 MB
        ]


async def test_seeded_filter_hides_dead_torrents_and_renumbers(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await pilot.press("f")
        await pilot.pause()

        table = _table_of(sort_app)
        assert "Debian 12 (no seeds)" not in _titles(table)
        assert table.row_count == 3
        # the No column must stay contiguous after filtering
        assert _numbers(table) == ["1", "2", "3"]


async def test_clear_filters_restores_full_relevance_view(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SEEDERS)
        await pilot.press("f")  # hide dead torrents
        await pilot.pause()
        assert _table_of(sort_app).row_count == 3

        await pilot.press("x")
        await pilot.pause()

        table = _table_of(sort_app)
        assert _titles(table) == [t.title for t in SORT_FIXTURE]


async def test_border_title_reports_filtered_count_and_sort(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        table = _table_of(sort_app)
        # unfiltered shows a bare total
        assert str(table.border_title) == "results (4) · relevance"

        await pilot.press("f")
        await pilot.pause()
        assert "3/4" in str(table.border_title)

        await _choose_sort(pilot, sort_app, SortKey.SEEDERS)
        # direction arrow shows which way the active sort runs
        assert "seeders ↓" in str(table.border_title)


async def test_sort_key_is_ignored_while_typing_in_search(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        search = sort_app.screen.query_one("SearchContent", SearchContent)
        search._search_input.focus()
        await pilot.press("s")
        await pilot.pause()

        # the Input consumes the key, so no menu opens and ordering is untouched
        assert not isinstance(sort_app.screen, SortSelectorScreen)
        assert _titles(_table_of(sort_app)) == [t.title for t in SORT_FIXTURE]


async def test_sort_menu_preselects_the_active_sort(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SIZE)

        await pilot.press("s")
        await pilot.pause()
        screen = sort_app.screen
        assert isinstance(screen, SortSelectorScreen)
        # reopening lands on the current field, so enter is a no-op
        assert screen.query_one(ListView).index == list(SortKey).index(SortKey.SIZE)


async def test_sort_menu_escape_cancels_without_reordering(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(sort_app.screen, SortSelectorScreen)

        # move the highlight, then back out
        await pilot.press("j")
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(sort_app.screen, SortSelectorScreen)
        assert _titles(_table_of(sort_app)) == [t.title for t in SORT_FIXTURE]


async def test_sort_menu_navigates_with_j_and_applies_on_enter(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await pilot.press("s")
        await pilot.pause()

        # relevance -> seeders is one step down the list
        await pilot.press("j")
        await pilot.press("enter")
        await pilot.pause()

        assert _titles(_table_of(sort_app))[0] == "Arch Linux ISO"  # 523 seeders


async def test_sort_menu_does_not_open_without_results(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    mock_indexer.search.return_value = []

    async with app.run_test() as pilot:
        await pilot.press("s")
        await pilot.pause()

        # nothing to sort, so the menu must stay shut
        assert not isinstance(app.screen, SortSelectorScreen)


async def test_malformed_sort_config_does_not_crash_startup(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    # config.set stores unparseable values verbatim, so the app must tolerate
    # them; raising here would make torrra unlaunchable until the user hand
    # edits config.toml
    mock_config.set("general.min_seeders", "abc")
    mock_config.set("general.default_sort", "not-a-column")
    mock_config.set("general.default_sort_order", "sideways")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test():
        table = _table_of(app)
        # falls back to relevance with no filtering
        assert _titles(table) == [t.title for t in SORT_FIXTURE]


async def test_configured_title_sort_loads_ascending(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    # regression: default_sort_order fell back to "desc" for every key, so a
    # configured title sort loaded Z-A instead of the natural A-Z
    mock_config.set("general.default_sort", "title")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test():
        table = _table_of(app)
        assert _titles(table) == sorted(t.title for t in SORT_FIXTURE)
        assert "title ↑" in str(table.border_title)


async def test_configured_seeders_sort_loads_descending(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    # the same defaulting must still give numeric keys their high-to-low order
    mock_config.set("general.default_sort", "seeders")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test():
        table = _table_of(app)
        assert _titles(table)[0] == "Arch Linux ISO"  # 523 seeders
        assert "seeders ↓" in str(table.border_title)


async def test_explicit_sort_order_overrides_the_natural_direction(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    mock_config.set("general.default_sort", "title")
    mock_config.set("general.default_sort_order", "desc")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test():
        table = _table_of(app)
        assert _titles(table) == sorted((t.title for t in SORT_FIXTURE), reverse=True)


async def test_clear_filters_restores_configured_sort_not_relevance(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    # x resets to the user's baseline, otherwise default_sort would only ever
    # apply at startup and be unreachable again for the rest of the session
    mock_config.set("general.default_sort", "seeders")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test() as pilot:
        await _choose_sort(pilot, app, SortKey.TITLE)
        assert _titles(_table_of(app))[0] == "Arch Linux ISO"

        await pilot.press("x")
        await pilot.pause()

        table = _table_of(app)
        assert _titles(table)[0] == "Arch Linux ISO"  # 523 seeders, not relevance
        assert "seeders ↓" in str(table.border_title)


async def test_clear_filters_restores_configured_min_seeders(
    app: TorrraApp, mock_indexer: MagicMock, mock_config: Config
):
    mock_config.set("general.min_seeders", "1")
    mock_indexer.search.return_value = list(SORT_FIXTURE)

    async with app.run_test() as pilot:
        # the configured floor already hides the dead torrent at startup
        assert _table_of(app).row_count == 3

        await pilot.press("f")  # toggle the floor off
        await pilot.pause()
        assert _table_of(app).row_count == 4

        await pilot.press("x")
        await pilot.pause()

        # back to the configured baseline, not to "show everything"
        assert _table_of(app).row_count == 3


async def _click_header(pilot: Pilot[TorrraApp], app: TorrraApp, col_key: str) -> None:
    """Click a column header the way a user would, via a real mouse event."""
    table = _table_of(app)
    # the table is bordered, so content starts inset from the widget origin
    inset_x = table.content_region.x - table.region.x
    inset_y = table.content_region.y - table.region.y

    x = inset_x
    for _, key, _ in SearchContent.COLS:
        width = table.columns[ColumnKey(key)].width
        span = width + table.cell_padding * 2
        if key == col_key:
            x += span // 2
            break
        x += span

    await pilot.click(table, offset=Offset(x, inset_y))
    await pilot.pause()


async def test_clicking_title_header_sorts_alphabetically(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _click_header(pilot, sort_app, "title_col")

        assert _titles(_table_of(sort_app)) == sorted(t.title for t in SORT_FIXTURE)


async def test_clicking_same_header_twice_toggles_direction(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _click_header(pilot, sort_app, "seeders_leechers_col")
        first = _titles(_table_of(sort_app))
        assert first[0] == "Arch Linux ISO"  # 523 seeders, highest first

        await _click_header(pilot, sort_app, "seeders_leechers_col")
        assert _titles(_table_of(sort_app)) == list(reversed(first))


async def test_clicking_size_header_sorts_numerically(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _click_header(pilot, sort_app, "size_col")

        sizes = [t.size for t in SORT_FIXTURE]
        table = _table_of(sort_app)
        by_title = {t.title: t.size for t in SORT_FIXTURE}
        assert [by_title[t] for t in _titles(table)] == sorted(sizes, reverse=True)


async def test_clicking_no_header_restores_indexer_order(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _click_header(pilot, sort_app, "title_col")
        assert _titles(_table_of(sort_app)) != [t.title for t in SORT_FIXTURE]

        await _click_header(pilot, sort_app, "no_col")
        assert _titles(_table_of(sort_app)) == [t.title for t in SORT_FIXTURE]


# jackett returns "Peers": null for some trackers, so a result set reaching the
# table can carry None where an int is annotated. sorting that mix used to
# raise TypeError inside _render_rows, which froze the table mid-update: the
# rows and border title kept their pre-crash values while the view model moved
# on, so an active filter looked like it had been cleared by the sort.
NULL_FIELD_FIXTURE = SORT_FIXTURE + [
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:nopeers",
        title="Tracker With No Peer Counts",
        size=1_000_000_000,
        seeders=None,  # pyright: ignore[reportArgumentType]
        leechers=None,  # pyright: ignore[reportArgumentType]
        source="MockIndexer",
    ),
]


@pytest.fixture
def null_field_app(app: TorrraApp, mock_indexer: MagicMock, mock_config: Config):
    mock_indexer.search.return_value = list(NULL_FIELD_FIXTURE)
    return app


async def test_missing_peer_counts_render_without_crashing(null_field_app: TorrraApp):
    async with null_field_app.run_test():
        assert len(_titles(_table_of(null_field_app))) == len(NULL_FIELD_FIXTURE)


@pytest.mark.parametrize(
    "key", [SortKey.LEECHERS, SortKey.SEEDERS, SortKey.SIZE, SortKey.TITLE]
)
async def test_sorting_survives_missing_peer_counts(
    null_field_app: TorrraApp, key: SortKey
):
    async with null_field_app.run_test() as pilot:
        await _choose_sort(pilot, null_field_app, key)

        # the table still holds every row, so the render completed rather than
        # aborting partway through
        assert len(_titles(_table_of(null_field_app))) == len(NULL_FIELD_FIXTURE)

        await pilot.press("S")
        await pilot.pause()
        assert len(_titles(_table_of(null_field_app))) == len(NULL_FIELD_FIXTURE)


async def test_unknown_peer_counts_sort_last(null_field_app: TorrraApp):
    async with null_field_app.run_test() as pilot:
        await _choose_sort(pilot, null_field_app, SortKey.LEECHERS)

        # unknown counts sink below a genuine 0 instead of ordering arbitrarily
        assert _titles(_table_of(null_field_app))[-1] == "Tracker With No Peer Counts"


async def test_filter_survives_a_sort_change(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await pilot.press("f")
        await pilot.pause()
        filtered = _titles(_table_of(sort_app))
        assert "Debian 12 (no seeds)" not in filtered

        await _choose_sort(pilot, sort_app, SortKey.SIZE)

        after = _titles(_table_of(sort_app))
        assert sorted(after) == sorted(filtered), (
            "sorting must not restore filtered rows"
        )
        assert "results (3/4)" in str(_table_of(sort_app).border_title)


async def test_filter_survives_a_header_click(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await pilot.press("f")
        await pilot.pause()
        filtered = _titles(_table_of(sort_app))

        await _click_header(pilot, sort_app, "title_col")

        assert _titles(_table_of(sort_app)) == sorted(filtered)
        assert "results (3/4)" in str(_table_of(sort_app).border_title)


async def test_sort_survives_a_filter_toggle(sort_app: TorrraApp):
    async with sort_app.run_test() as pilot:
        await _choose_sort(pilot, sort_app, SortKey.SIZE)
        await pilot.press("f")
        await pilot.pause()

        table = _table_of(sort_app)
        by_title = {t.title: t.size for t in SORT_FIXTURE}
        shown = [by_title[t] for t in _titles(table)]
        assert shown == sorted(shown, reverse=True), "filtering must not drop the sort"
        assert "size" in str(table.border_title)


# real result sets run to thousands of rows with five-digit swarm counts, so
# row numbers and S:L both outgrow the widths their columns are declared with
WIDE_VALUE_FIXTURE = [
    Torrent(
        magnet_uri=f"magnet:?xt=urn:btih:wide{i}",
        title=f"Wide Release {i:03d}",
        size=1_000_000_000 + i,
        seeders=15128 - i,
        leechers=10059 - i,
        source="MockIndexer",
    )
    for i in range(150)
]

# the widest cell here belongs to the only unseeded release, so hiding it with
# the seeded-only filter should hand the column width back
WIDE_UNSEEDED_FIXTURE = [
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:busy",
        title="Unseeded But Busy",
        size=1_000_000_000,
        seeders=0,
        leechers=1_234_567,
        source="MockIndexer",
    ),
    Torrent(
        magnet_uri="magnet:?xt=urn:btih:calm",
        title="Calm Release",
        size=2_000_000_000,
        seeders=12,
        leechers=34,
        source="MockIndexer",
    ),
]


@pytest.fixture
def wide_value_app(app: TorrraApp, mock_indexer: MagicMock, mock_config: Config):
    mock_indexer.search.return_value = list(WIDE_VALUE_FIXTURE)
    return app


@pytest.fixture
def wide_unseeded_app(app: TorrraApp, mock_indexer: MagicMock, mock_config: Config):
    mock_indexer.search.return_value = list(WIDE_UNSEEDED_FIXTURE)
    return app


def _col_width(table: DataTable[str], key: str) -> int:
    return table.columns[ColumnKey(key)].width


def _rendered(table: DataTable[str]) -> str:
    """Exactly what the table paints, so clipped cells can't pass unnoticed."""
    lines = table.render_lines(Region(0, 0, table.size.width, table.size.height))
    return "\n".join("".join(segment.text for segment in line) for line in lines)


async def test_wide_swarm_counts_are_not_clipped_on_screen(wide_value_app: TorrraApp):
    """Sorting by leechers puts the widest counts on top, which is exactly
    where a too-narrow S:L column used to cut them off and make a correct
    ordering read as broken."""
    async with wide_value_app.run_test(size=(120, 40)) as pilot:
        await _choose_sort(pilot, wide_value_app, SortKey.LEECHERS)

        table = _table_of(wide_value_app)
        assert table.get_cell_at(Coordinate(0, 3)) == "15128:10059"
        assert "15128:10059" in _rendered(table), "widest S:L cell is being clipped"


async def test_fixed_columns_widen_to_fit_their_content(wide_value_app: TorrraApp):
    async with wide_value_app.run_test(size=(120, 40)) as pilot:
        await _choose_sort(pilot, wide_value_app, SortKey.LEECHERS)
        table = _table_of(wide_value_app)

        for index, (_, key, _) in enumerate(SearchContent.COLS):
            if key == "title_col":  # absorbs whatever width is left over
                continue
            widest = max(
                len(str(table.get_cell_at(Coordinate(row, index))))
                for row in range(table.row_count)
            )
            assert _col_width(table, key) >= widest, f"{key} clips its own content"


async def test_columns_stay_at_their_declared_width_for_small_values(
    sort_app: TorrraApp,
):
    async with sort_app.run_test():
        table = _table_of(sort_app)
        declared = {key: width for _, key, width in SearchContent.COLS}

        assert _col_width(table, "no_col") == declared["no_col"]
        assert _col_width(table, "size_col") == declared["size_col"]
        assert (
            _col_width(table, "seeders_leechers_col")
            == declared["seeders_leechers_col"]
        )


async def test_filtering_out_the_widest_row_gives_the_width_back(
    wide_unseeded_app: TorrraApp,
):
    async with wide_unseeded_app.run_test(size=(120, 40)) as pilot:
        table = _table_of(wide_unseeded_app)
        assert _col_width(table, "seeders_leechers_col") == len("0:1234567")

        await pilot.press("f")  # hide the unseeded release
        await pilot.pause()

        assert _col_width(table, "seeders_leechers_col") == 6, (
            "column should shrink back to its declared width"
        )


async def test_title_column_keeps_a_usable_width_in_a_narrow_terminal(
    wide_value_app: TorrraApp,
):
    async with wide_value_app.run_test(size=(40, 20)) as pilot:
        await _choose_sort(pilot, wide_value_app, SortKey.LEECHERS)

        table = _table_of(wide_value_app)
        declared = {key: width for _, key, width in SearchContent.COLS}
        assert _col_width(table, "title_col") >= declared["title_col"]
