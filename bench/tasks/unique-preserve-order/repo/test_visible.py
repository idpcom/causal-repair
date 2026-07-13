"""Visible failing test (stdlib only)."""
import sys

from seq import unique


def check():
    assert unique([3, 1, 3, 2, 1]) == [3, 1, 2]  # order must be preserved


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
