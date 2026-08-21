import pytest

from torrra.utils.helpers import (
    get_tomllib,
    human_readable_eta,
    human_readable_size,
    lazy_import,
)


def test_human_readable_size():
    assert human_readable_size(1023) == "1023.00 B"
    assert human_readable_size(1024) == "1.00 KB"
    assert human_readable_size(1500) == "1.46 KB"
    assert human_readable_size(1024 * 1024 * 5) == "5.00 MB"
    assert human_readable_size(1024**4) == "1.00 TB"


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
