"""Hidden contract test (never shown to the model)."""
import sys

from flagset import decode_flags


def check():
    assert decode_flags("read, Write") == {"read", "write"}
    assert decode_flags("EXEC,,admin,") == {"exec", "admin"}
    assert decode_flags("") == set()
    try:
        decode_flags("read,foo")
    except KeyError:
        pass
    else:
        raise AssertionError('decode_flags("read,foo")' + ' must raise KeyError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
