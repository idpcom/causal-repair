"""Visible failing test (stdlib only)."""
import sys

from display import format_name


def check():
    assert format_name("alice") == "Alice"
    assert format_name("legacy") == "Anonymous"


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
