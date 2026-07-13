"""Hidden contract test (never shown to the model)."""
import sys

from config import get_int


def check():
    assert get_int({"n": "8"}, "n", 1, 16) == 8
    assert get_int({"n": "0x10"}, "n", 1, 32) == 16
    assert get_int({"n": " 12 "}, "n", 1, 16) == 12
    try:
        get_int({"n": "99"}, "n", 1, 16)
    except ValueError:
        pass
    else:
        raise AssertionError('get_int({"n": "99"}, "n", 1, 16)' + ' must raise ValueError')
    try:
        get_int({"n": "0"}, "n", 1, 16)
    except ValueError:
        pass
    else:
        raise AssertionError('get_int({"n": "0"}, "n", 1, 16)' + ' must raise ValueError')
    try:
        get_int({"n": "abc"}, "n", 1, 16)
    except ValueError:
        pass
    else:
        raise AssertionError('get_int({"n": "abc"}, "n", 1, 16)' + ' must raise ValueError')
    try:
        get_int({}, "n", 1, 16)
    except KeyError:
        pass
    else:
        raise AssertionError('get_int({}, "n", 1, 16)' + ' must raise KeyError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
