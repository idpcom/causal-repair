class Account:
    """Simple account with a no-overdraft contract."""

    def __init__(self):
        self._balance = 0

    def deposit(self, x):
        if not isinstance(x, (int, float)) or x <= 0:
            raise ValueError(f"deposit must be positive, got {x!r}")
        self._balance += x

    def withdraw(self, x):
        if not isinstance(x, (int, float)) or x <= 0:
            raise ValueError(f"withdraw must be positive, got {x!r}")
        if x > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= x
        return self._balance

    def balance(self):
        return self._balance
