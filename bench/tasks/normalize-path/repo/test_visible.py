"""Visible failing test (stdlib only)."""
import sys

from pathnorm import normalize_path


def check():
    assert normalize_path("/a//b") == "/a/b"
    assert normalize_path("/a/b/") == "/a/b"


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
