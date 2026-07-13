"""Visible failing test shown to the model (stdlib only, no pytest)."""
import sys

from profile import get_display_name


def check():
    assert get_display_name("alice") == "Alice", "normal name should be stripped"
    assert get_display_name("legacy") == "Anonymous", "null legacy name should become Anonymous"


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001 - report any failure as a test failure
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
