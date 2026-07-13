"""Hidden contract test (never shown to the model)."""
import sys

from intervals import merge


def check():
    assert merge([[3, 4], [1, 2]]) == [[1, 2], [3, 4]]
    assert merge([[1, 3], [2, 6]]) == [[1, 6]]
    assert merge([[1, 2], [2, 3]]) == [[1, 3]]
    assert merge([]) == []
    assert merge([[5, 5]]) == [[5, 5]]
    try:
        merge([[2, 1]])
    except ValueError:
        pass
    else:
        raise AssertionError('merge([[2, 1]])' + ' must raise ValueError')
    try:
        merge([[1, 2], [9, 3]])
    except ValueError:
        pass
    else:
        raise AssertionError('merge([[1, 2], [9, 3]])' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
