"""Hidden contract test (never shown to the model)."""
import sys

from version import parse_version


def check():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("1.2") == (1, 2, 0)
    assert parse_version("10.0.7") == (10, 0, 7)
    try:
        parse_version("1")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_version("1")' + ' must raise ValueError')
    try:
        parse_version("1.2.3.4")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_version("1.2.3.4")' + ' must raise ValueError')
    try:
        parse_version("1.x")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_version("1.x")' + ' must raise ValueError')
    try:
        parse_version("banana")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_version("banana")' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
