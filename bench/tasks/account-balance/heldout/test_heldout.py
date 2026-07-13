"""Hidden contract test (never shown to the model)."""
import sys

from account import Account


def check():
    a = Account()
    a.deposit(100)
    assert a.withdraw(30) == 70
    try:
        a.withdraw(1000)
    except ValueError:
        pass
    else:
        raise AssertionError('a.withdraw(1000)' + ' must raise ValueError')
    assert a.balance() == 70, "failed overdraft must not change balance"
    try:
        a.deposit(0)
    except ValueError:
        pass
    else:
        raise AssertionError('a.deposit(0)' + ' must raise ValueError')
    try:
        a.withdraw(-5)
    except ValueError:
        pass
    else:
        raise AssertionError('a.withdraw(-5)' + ' must raise ValueError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
