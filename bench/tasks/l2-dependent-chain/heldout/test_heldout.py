"""Hidden contract test (never shown to the model)."""
import sys

from records import parse_lines
from stats import count_records


def check():
    assert parse_lines("a\nb") == ["a", "b"]
    assert parse_lines("a\nb\n") == ["a", "b"]
    assert parse_lines(" a \n\nb") == ["a", "b"]
    assert count_records("a\nb") == 2
    assert count_records("a\nb\n  ") == 2
    assert count_records("") == 0
    assert count_records("a\nb") == len(parse_lines("a\nb"))


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
