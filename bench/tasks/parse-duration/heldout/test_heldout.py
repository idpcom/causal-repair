"""Hidden contract test (never shown to the model)."""
import sys

from duration import parse_duration


def check():
    assert parse_duration("30s") == 30
    assert parse_duration("5m") == 300
    assert parse_duration("2h") == 7200
    assert parse_duration(" 10m ") == 600
    assert parse_duration("45") == 45
    try:
        parse_duration("")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_duration("")' + ' must raise ValueError')
    try:
        parse_duration("5x")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_duration("5x")' + ' must raise ValueError')
    try:
        parse_duration("m")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_duration("m")' + ' must raise ValueError')
    try:
        parse_duration("1.5h")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_duration("1.5h")' + ' must raise ValueError')
    try:
        parse_duration("abc")
    except ValueError:
        pass
    else:
        raise AssertionError('parse_duration("abc")' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
