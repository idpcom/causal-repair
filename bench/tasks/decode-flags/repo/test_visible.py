"""Visible failing test (stdlib only)."""
import sys

from flagset import decode_flags


def check():
    assert decode_flags("read, Write") == {"read", "write"}


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
