"""Visible failing test (stdlib only)."""
import sys

from stats import count_records


def check():
    assert count_records("a\nb") == 2
    assert count_records("a\nb\n  ") == 2


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
