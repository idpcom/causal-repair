"""Visible failing test (stdlib only)."""
import sys

from daterange import days_inclusive


def check():
    # Jan 1..Jan 3 inclusive is 3 days, not 2.
    assert days_inclusive("2024-01-01", "2024-01-03") == 3, "endpoints must both count"
    assert days_inclusive("2024-01-01", "2024-01-01") == 1, "single day is 1"


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
