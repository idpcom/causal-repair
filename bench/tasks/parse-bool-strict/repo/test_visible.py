"""Visible failing test (stdlib only)."""
import sys

from flags import parse_bool


def check():
    assert parse_bool("true") is True
    assert parse_bool("1") is True   # currently unhandled -> KeyError
    assert parse_bool("0") is False


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
