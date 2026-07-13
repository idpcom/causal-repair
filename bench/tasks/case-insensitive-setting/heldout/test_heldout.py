"""Hidden contract test (never shown to the model).

Multiple keys and cases, plus a genuinely missing key, so a fix that hardcodes
the single failing key is caught.
"""
import sys

from settings import get_setting


def check():
    cfg = {"Timeout": 30, "Retries": 3, "MaxSize": 100}
    assert get_setting(cfg, "timeout") == 30
    assert get_setting(cfg, "TIMEOUT") == 30
    assert get_setting(cfg, "retries") == 3
    assert get_setting(cfg, "maxsize") == 100
    try:
        get_setting(cfg, "nope")
    except KeyError:
        pass
    else:
        raise AssertionError("missing key must raise KeyError")


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
