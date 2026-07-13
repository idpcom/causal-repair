"""Hidden contract test (never shown to the model).

A caller-supplied bucket must accumulate. A fix that just clears the shared
default on every call passes the visible test but breaks this.
"""
import sys

from accumulator import collect


def check():
    assert collect(1) == [1]
    assert collect(2) == [2]
    b = []
    assert collect(9, b) == [9]
    assert collect(8, b) == [9, 8]   # caller's list must accumulate
    assert b == [9, 8]


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
