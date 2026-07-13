class Account:
    def __init__(self):
        self._balance = 0

    def deposit(self, x):
        self._balance += x

    def withdraw(self, x):
        self._balance = max(0, self._balance - x)
        return self._balance

    def balance(self):
        return self._balance
