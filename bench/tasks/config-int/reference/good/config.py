def get_int(cfg, key, lo, hi):
    """Read cfg[key] (a string) as an integer with an inclusive range."""
    raw = cfg[key].strip()
    if raw.lower().startswith("0x"):
        if not all(c in "0123456789abcdef" for c in raw[2:].lower()) or not raw[2:]:
            raise ValueError(f"not an integer: {raw!r}")
        value = int(raw, 16)
    else:
        if not raw.isdigit():
            raise ValueError(f"not an integer: {raw!r}")
        value = int(raw)
    if value < lo or value > hi:
        raise ValueError(f"{value} outside [{lo}, {hi}]")
    return value
