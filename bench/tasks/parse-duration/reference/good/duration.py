UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text):
    """Parse a duration string into seconds."""
    t = text.strip()
    if t and t[-1] in UNITS and t[:-1].strip():
        amount, mult = t[:-1].strip(), UNITS[t[-1]]
    else:
        amount, mult = t, 1
    if not amount.isdigit():
        raise ValueError(f"invalid duration: {text!r}")
    return int(amount) * mult
