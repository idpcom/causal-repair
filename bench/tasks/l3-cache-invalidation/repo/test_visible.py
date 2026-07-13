"""Visible failing test (stdlib only)."""
import sys

import kvstore
import search


def check():
    kvstore.set_item("apple", 1)
    kvstore.set_item("apricot", 2)
    assert search.find("ap") == ["apple", "apricot"]
    kvstore.set_item("avocado", 3)
    assert search.find("a") == ["apple", "apricot", "avocado"]


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
