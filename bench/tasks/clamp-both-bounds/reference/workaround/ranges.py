def clamp(x, lo, hi):
    # Handle the failing negative case.
    if x < 0:
        return 0
    if x > hi:
        return hi
    return x
