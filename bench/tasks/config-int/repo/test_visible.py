"""Visible failing test (stdlib only)."""
import sys

from config import get_int


def check():
    assert get_int({"n": "8"}, "n", 1, 16) == 8
    assert get_int({"n": "0x10"}, "n", 1, 32) == 16


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
