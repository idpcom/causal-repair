"""Hidden contract test (never shown to the model).

Encodes the full intended contract, mirroring the three assertions that
scripts/evaluate-fixtures.py uses so this task reproduces the reference
good-vs-bad grading exactly.
"""
import sys

from profile import get_display_name


def check():
    assert get_display_name("alice") == "Alice"
    assert get_display_name("legacy") == "Anonymous"
    try:
        get_display_name("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("missing user must still raise KeyError")


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
