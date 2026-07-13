"""Hidden contract test (never shown to the model)."""
import sys

from bstack import BoundedStack


def check():
    s = BoundedStack(2)
    s.push(1)
    s.push(2)
    try:
        s.push(3)
    except OverflowError:
        pass
    else:
        raise AssertionError('s.push(3)' + ' must raise OverflowError')
    assert s.pop() == 2
    assert s.pop() == 1
    try:
        s.pop()
    except IndexError:
        pass
    else:
        raise AssertionError('s.pop()' + ' must raise IndexError')
    try:
        BoundedStack(0)
    except ValueError:
        pass
    else:
        raise AssertionError('BoundedStack(0)' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
