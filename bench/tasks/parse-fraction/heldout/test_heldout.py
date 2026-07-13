"""Hidden contract test (never shown to the model)."""
import sys

from fraction import parse_fraction


def check():
    assert parse_fraction("3/4") == 0.75
    assert parse_fraction("3") == 3.0
    assert parse_fraction(" 1 / 2 ") == 0.5
    try:
        parse_fraction("1/0")
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError('parse_fraction("1/0")' + ' must raise ZeroDivisionError')
    try:
        parse_fraction("a/b")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_fraction("a/b")' + ' must raise ValueError')
    try:
        parse_fraction("1/2/3")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_fraction("1/2/3")' + ' must raise ValueError')
    try:
        parse_fraction("")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_fraction("")' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
