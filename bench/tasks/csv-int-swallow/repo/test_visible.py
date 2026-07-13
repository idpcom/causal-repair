"""Visible failing test (stdlib only)."""
import sys

from csvparse import parse_ints


def check():
    assert parse_ints("1,2,3") == [1, 2, 3]
    assert parse_ints("10,20,") == [10, 20]  # trailing comma must be tolerated


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
