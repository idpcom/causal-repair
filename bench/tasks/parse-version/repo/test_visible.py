"""Visible failing test (stdlib only)."""
import sys

from version import parse_version


def check():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("1.2") == (1, 2, 0)


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
