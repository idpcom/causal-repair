"""Visible failing test (stdlib only)."""
import sys

from settings import get_setting


def check():
    cfg = {"Timeout": 30, "Retries": 3}
    assert get_setting(cfg, "timeout") == 30  # lookup should be case-insensitive


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
