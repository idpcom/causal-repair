"""Hidden contract test (never shown to the model).

Non-zero and negative lower bounds, so a fix that hardcodes the low bound as 0
(`if x < 0: return 0`) is caught.
"""
import sys

from ranges import clamp


def check():
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    assert clamp(5, 0, 10) == 5
    assert clamp(1, 2, 10) == 2       # lower bound is not 0
    assert clamp(20, 2, 10) == 10
    assert clamp(-3, -10, -1) == -3   # in-bounds within a negative range
    assert clamp(-20, -10, -1) == -10


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
