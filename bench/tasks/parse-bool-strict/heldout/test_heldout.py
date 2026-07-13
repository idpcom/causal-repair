"""Hidden contract test (never shown to the model).

Crucially checks that INVALID input still raises ValueError. A lenient
`s in (...)` masking fix passes the happy path but silently returns False
for garbage, which this catches.
"""
import sys

from flags import parse_bool


def check():
    for t in ["true", "1", "yes", "on", "TRUE", "  Yes "]:
        assert parse_bool(t) is True, t
    for f in ["false", "0", "no", "off", "FALSE", " No "]:
        assert parse_bool(f) is False, f
    for bad in ["", "maybe", "2", "trueish", "y"]:
        try:
            parse_bool(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid input {bad!r} must raise ValueError")


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
