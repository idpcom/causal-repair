class BoundedStack:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = []

    def push(self, x):
        if len(self._items) < self.capacity:
            self._items.append(x)

    def pop(self):
        return self._items.pop()
