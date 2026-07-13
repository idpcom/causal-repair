"""Visible failing test (stdlib only)."""
import sys

from duration import parse_duration


def check():
    assert parse_duration("30s") == 30
    assert parse_duration("5m") == 300
    assert parse_duration("45") == 45


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
