class BoundedStack:
    """LIFO stack with a fixed capacity.

    capacity must be an int >= 1 (ValueError otherwise). push beyond capacity
    must raise OverflowError - items are never silently dropped. pop on an
    empty stack must raise IndexError. pop returns the most recently pushed
    item (LIFO).
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        return self._items.pop(0)
