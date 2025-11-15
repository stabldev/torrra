import pytest

from torrra.utils.helpers import human_readable_size, lazy_import


def test_human_readable_size():
    assert human_readable_size(1023) == "1023.00 B"
    assert human_readable_size(1024) == "1.00 KB"
    assert human_readable_size(1500) == "1.46 KB"
    assert human_readable_size(1024 * 1024 * 5) == "5.00 MB"
    assert human_readable_size(1024**4) == "1.00 TB"


def test_lazy_import():
    sqrt = lazy_import("math.sqrt")
    assert sqrt(25) == 5


def test_lazy_import_failure():
    with pytest.raises(ImportError) as exc:
        lazy_import("nonexistent_mod.func")

    assert "nonexistent_mod.func" in str(exc.value)
    assert "No module named" in str(exc.value)
