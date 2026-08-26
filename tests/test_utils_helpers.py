import pytest

from torrra.utils.helpers import (
    coerce_ratio_limit,
    coerce_seeding_time,
    coerce_speed_limit,
    format_ratio_limit,
    format_seeding_time,
    get_tomllib,
    human_readable_eta,
    human_readable_size,
    lazy_import,
    parse_ratio_limit,
    parse_seeding_time,
    parse_speed_limit,
)


def test_human_readable_size():
    assert human_readable_size(1023) == "1023.00 B"
    assert human_readable_size(1024) == "1.00 KB"
    assert human_readable_size(1500) == "1.46 KB"
    assert human_readable_size(1024 * 1024 * 5) == "5.00 MB"
    assert human_readable_size(1024**4) == "1.00 TB"


def test_human_readable_size_short():
    assert human_readable_size(820, short=True) == "820 B"
    assert human_readable_size(10240, short=True) == "10 KB"
    assert human_readable_size(500 * 1024, short=True) == "500 KB"
    assert human_readable_size(1536 * 1024, short=True) == "1.5 MB"
    assert human_readable_size(20 * 1024**2, short=True) == "20 MB"
    assert human_readable_size(int(1.5 * 1024**3), short=True) == "1.5 GB"
    assert human_readable_size(2 * 1024**4, short=True) == "2 TB"
    assert human_readable_size(3 * 1024**5, short=True) == "3 PB"


def test_human_readable_eta():
    assert human_readable_eta(None) == "∞"
    assert human_readable_eta(None, is_seeding=True) == "∞"
    assert human_readable_eta(100, is_seeding=True) == "∞"
    assert human_readable_eta(0) == "0s"
    assert human_readable_eta(45) == "45s"
    assert human_readable_eta(60) == "1m"
    assert human_readable_eta(125) == "2m 5s"
    assert human_readable_eta(3600) == "1h"
    assert human_readable_eta(3665) == "1h 1m"
    assert human_readable_eta(86400) == "1d"
    assert human_readable_eta(90000) == "1d 1h"
    assert human_readable_eta(-10) == "∞"


def test_lazy_import():
    sqrt = lazy_import("math.sqrt")
    assert sqrt(25) == 5


def test_lazy_import_failure():
    with pytest.raises(ImportError) as exc:
        lazy_import("nonexistent_mod.func")

    assert "nonexistent_mod.func" in str(exc.value)
    assert "No module named" in str(exc.value)


def test_get_tomllib():
    tomllib = get_tomllib()
    assert hasattr(tomllib, "load")
    assert hasattr(tomllib, "loads")
    assert hasattr(tomllib, "TOMLDecodeError")
    parsed = tomllib.loads('key = "value"')
    assert parsed == {"key": "value"}


def test_parse_speed_limit_unlimited():
    assert parse_speed_limit("") == -1
    assert parse_speed_limit("0") == -1
    assert parse_speed_limit("unlimited") == -1
    assert parse_speed_limit("off") == -1
    assert parse_speed_limit("  NONE ") == -1


def test_parse_speed_limit_units():
    assert parse_speed_limit("500K") == 500 * 1024
    assert parse_speed_limit("2M") == 2 * 1024**2
    assert parse_speed_limit("1.5M") == int(1.5 * 1024**2)
    assert parse_speed_limit("1G") == 1024**3
    assert parse_speed_limit("1024") == 1024


def test_parse_speed_limit_per_sec_suffix():
    assert parse_speed_limit("500 KB/s") == 500 * 1024
    assert parse_speed_limit("2MB/s") == 2 * 1024**2
    assert parse_speed_limit("1.5 GB/s") == int(1.5 * 1024**3)
    assert parse_speed_limit("10k/s") == 10 * 1024


def test_parse_speed_limit_invalid():
    with pytest.raises(ValueError):
        parse_speed_limit("abc")
    with pytest.raises(ValueError):
        parse_speed_limit("-5")
    with pytest.raises(ValueError):
        parse_speed_limit("10X")


def test_coerce_speed_limit():
    assert coerce_speed_limit(10240) == 10240
    assert coerce_speed_limit("10 KB/s") == 10 * 1024
    assert coerce_speed_limit("2M") == 2 * 1024**2
    assert coerce_speed_limit("500K") == 500 * 1024
    assert coerce_speed_limit("0") == 0
    assert coerce_speed_limit("unlimited") == 0
    assert coerce_speed_limit("off") == 0
    assert coerce_speed_limit(0) == 0
    assert coerce_speed_limit(-100) == 0
    assert coerce_speed_limit(False) == 0
    assert coerce_speed_limit(True) == 0
    assert coerce_speed_limit("invalid-unit") == 0


def test_parse_ratio_limit():
    assert parse_ratio_limit("") == -1.0
    assert parse_ratio_limit("0") == -1.0
    assert parse_ratio_limit("0.0") == -1.0
    assert parse_ratio_limit("unlimited") == -1.0
    assert parse_ratio_limit("off") == -1.0
    assert parse_ratio_limit("none") == -1.0
    assert parse_ratio_limit("1.5") == 1.5
    assert parse_ratio_limit("2") == 2.0
    assert parse_ratio_limit("0.75") == 0.75

    with pytest.raises(ValueError):
        parse_ratio_limit("-1")
    with pytest.raises(ValueError):
        parse_ratio_limit("abc")


def test_format_ratio_limit():
    assert format_ratio_limit(None) == ""
    assert format_ratio_limit(0) == ""
    assert format_ratio_limit(-1) == ""
    assert format_ratio_limit(1.5) == "1.5"
    assert format_ratio_limit(2.0) == "2"
    assert format_ratio_limit(2.25) == "2.25"


def test_coerce_ratio_limit():
    assert coerce_ratio_limit(1.5) == 1.5
    assert coerce_ratio_limit(2) == 2.0
    assert coerce_ratio_limit("1.5") == 1.5
    assert coerce_ratio_limit("0") == 0.0
    assert coerce_ratio_limit("unlimited") == 0.0
    assert coerce_ratio_limit(False) == 0.0
    assert coerce_ratio_limit("invalid") == 0.0


def test_parse_seeding_time():
    assert parse_seeding_time("") == -1
    assert parse_seeding_time("0") == -1
    assert parse_seeding_time("unlimited") == -1
    assert parse_seeding_time("off") == -1
    assert parse_seeding_time("none") == -1
    assert parse_seeding_time("30") == 30
    assert parse_seeding_time("30m") == 30
    assert parse_seeding_time("30 min") == 30
    assert parse_seeding_time("30 minutes") == 30
    assert parse_seeding_time("2h") == 120
    assert parse_seeding_time("1.5h") == 90
    assert parse_seeding_time("2 hours") == 120
    assert parse_seeding_time("1d") == 1440
    assert parse_seeding_time("2 days") == 2880

    with pytest.raises(ValueError):
        parse_seeding_time("-5")
    with pytest.raises(ValueError):
        parse_seeding_time("invalid")


def test_format_seeding_time():
    assert format_seeding_time(None) == ""
    assert format_seeding_time(0) == ""
    assert format_seeding_time(-1) == ""
    assert format_seeding_time(45) == "45m"
    assert format_seeding_time(60) == "1h"
    assert format_seeding_time(120) == "2h"
    assert format_seeding_time(1440) == "1d"
    assert format_seeding_time(2880) == "2d"


def test_coerce_seeding_time():
    assert coerce_seeding_time(60) == 60
    assert coerce_seeding_time("2h") == 120
    assert coerce_seeding_time("30m") == 30
    assert coerce_seeding_time("0") == 0
    assert coerce_seeding_time("unlimited") == 0
    assert coerce_seeding_time(False) == 0
    assert coerce_seeding_time("invalid") == 0
