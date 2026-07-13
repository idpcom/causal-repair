def clamp(x, lo, hi):
    """Constrain x to the inclusive range [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
