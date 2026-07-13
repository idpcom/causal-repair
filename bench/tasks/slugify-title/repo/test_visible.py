"""Visible failing test (stdlib only)."""
import sys

from textutil import slugify


def check():
    assert slugify("Hello, World!") == "hello-world"


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
