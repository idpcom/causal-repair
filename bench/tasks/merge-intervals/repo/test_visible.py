"""Visible failing test (stdlib only)."""
import sys

from intervals import merge


def check():
    assert merge([[3, 4], [1, 2]]) == [[1, 2], [3, 4]]
    assert merge([[1, 3], [2, 6]]) == [[1, 6]]


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
