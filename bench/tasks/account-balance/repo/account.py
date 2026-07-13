class Account:
    """Simple account.

    deposit(x) and withdraw(x) require x > 0, else ValueError.
    withdraw(x) returns the new balance. Withdrawing more than the balance
    must raise ValueError and leave the balance unchanged (no overdraft,
    no silent clamping).
    """

    def __init__(self):
        self._balance = 0

    def deposit(self, x):
        self._balance += x

    def withdraw(self, x):
        self._balance -= x

    def balance(self):
        return self._balance
