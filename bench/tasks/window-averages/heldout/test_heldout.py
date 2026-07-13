"""Hidden contract test (never shown to the model)."""
import sys

from windows import window_averages


def check():
    assert window_averages([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
    assert window_averages([1, 2, 3], 3) == [2.0]
    assert window_averages([1, 2], 3) == []
    assert window_averages([], 1) == []
    try:
        window_averages([1, 2], 0)
    except ValueError:
        pass
    else:
        raise AssertionError('window_averages([1, 2], 0)' + ' must raise ValueError')
    try:
        window_averages([1, 2], -1)
    except ValueError:
        pass
    else:
        raise AssertionError('window_averages([1, 2], -1)' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
