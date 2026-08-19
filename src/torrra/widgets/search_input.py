from textual.widgets import Input
from typing_extensions import override


class SearchInput(Input):
    """A search input widget that yields the '?' binding when empty."""

    @override
    def check_consume_key(self, key: str, character: str | None) -> bool:
        if (key == "question_mark" or character == "?") and not self.value.strip():
            return False
        return super().check_consume_key(key, character)

