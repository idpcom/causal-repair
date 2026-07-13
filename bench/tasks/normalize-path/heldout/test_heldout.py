"""Hidden contract test (never shown to the model)."""
import sys

from pathnorm import normalize_path


def check():
    assert normalize_path("/a//b") == "/a/b"
    assert normalize_path("/a///b//c") == "/a/b/c"
    assert normalize_path("/a/b/") == "/a/b"
    assert normalize_path("/") == "/"
    assert normalize_path("///") == "/"
    try:
        normalize_path("rel/x")
    except ValueError:
        pass
    else:
        raise AssertionError('normalize_path("rel/x")' + ' must raise ValueError')
    try:
        normalize_path("")
    except ValueError:
        pass
    else:
        raise AssertionError('normalize_path("")' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
