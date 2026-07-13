"""Visible failing test (stdlib only)."""
import sys

from accumulator import collect


def check():
    assert collect(1) == [1]
    assert collect(2) == [2]  # a fresh call must not remember the previous one


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
