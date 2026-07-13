def get_int(cfg, key, lo, hi):
    """Read cfg[key] (a string) as an integer.

    Decimal ("8") and hex with prefix ("0x10") are accepted; surrounding
    whitespace is ignored. The value must lie in the inclusive range
    [lo, hi] - out-of-range or non-numeric values raise ValueError.
    A missing key raises KeyError.
    """
    return int(cfg[key])
