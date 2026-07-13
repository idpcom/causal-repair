def parse_fraction(text):
    """Parse "N/D" or a whole number "N" into a float."""
    parts = [p.strip() for p in text.split("/")]
    if len(parts) == 1:
        if not parts[0].isdigit():
            raise ValueError(f"invalid fraction: {text!r}")
        return float(parts[0])
    if len(parts) != 2:
        raise ValueError(f"invalid fraction: {text!r}")
    num, den = parts
    if not num.isdigit() or not den.isdigit():
        raise ValueError(f"invalid fraction: {text!r}")
    return int(num) / int(den)
