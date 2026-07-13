"""Visible failing test (stdlib only)."""
import sys

from fraction import parse_fraction


def check():
    assert parse_fraction("3/4") == 0.75
    assert parse_fraction("3") == 3.0


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
