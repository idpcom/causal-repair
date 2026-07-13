class BoundedStack:
    """LIFO stack with a fixed capacity."""

    def __init__(self, capacity):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError(f"capacity must be an int >= 1, got {capacity!r}")
        self.capacity = capacity
        self._items = []

    def push(self, x):
        if len(self._items) >= self.capacity:
            raise OverflowError("stack is full")
        self._items.append(x)

    def pop(self):
        return self._items.pop()
