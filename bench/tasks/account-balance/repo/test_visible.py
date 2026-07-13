"""Visible failing test (stdlib only)."""
import sys

from account import Account


def check():
    a = Account()
    a.deposit(100)
    assert a.withdraw(30) == 70
    assert a.balance() == 70


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"VISIBLE FAIL: {exc!r}")
        sys.exit(1)
    print("VISIBLE OK")
