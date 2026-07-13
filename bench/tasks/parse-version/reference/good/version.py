def parse_version(text):
    """Parse "MAJOR.MINOR.PATCH" or "MAJOR.MINOR" into a tuple of ints."""
    parts = text.split(".")
    if len(parts) not in (2, 3):
        raise ValueError(f"invalid version: {text!r}")
    if not all(p.isdigit() for p in parts):
        raise ValueError(f"invalid version: {text!r}")
    if len(parts) == 2:
        parts.append("0")
    return tuple(int(p) for p in parts)
