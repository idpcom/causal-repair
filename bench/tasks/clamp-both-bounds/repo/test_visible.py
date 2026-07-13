"""Visible failing test (stdlib only)."""
import sys

from ranges import clamp


def check():
    assert clamp(-5, 0, 10) == 0    # currently not clamped at the low end
    assert clamp(15, 0, 10) == 10
    assert clamp(5, 0, 10) == 5


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
