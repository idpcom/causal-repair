def clamp(x, lo, hi):
    """Constrain x to the inclusive range [lo, hi]."""
    if x > hi:
        return hi
    return x
