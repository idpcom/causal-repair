"""Hidden contract test (never shown to the model)."""
import sys

from display import format_name
from badge import make_badge
from models import get_user


def check():
    assert format_name("alice") == "Alice"
    assert format_name("legacy") == "Anonymous"
    assert make_badge("alice") == "ALICE"
    assert make_badge("legacy") == "ANONYMOUS"
    try:
        get_user("nope")
    except KeyError:
        pass
    else:
        raise AssertionError('get_user("nope")' + ' must raise KeyError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
