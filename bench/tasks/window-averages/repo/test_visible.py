"""Visible failing test (stdlib only)."""
import sys

from windows import window_averages


def check():
    assert window_averages([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
