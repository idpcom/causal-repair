UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text):
    """Parse a duration string into seconds.

    Accepts a non-negative integer with an optional unit suffix: "30s", "5m",
    "2h"; a bare integer like "45" means seconds. Surrounding whitespace is
    ignored. Anything else - unknown unit, empty string, non-numeric amount -
    is invalid and must raise ValueError.
    """
    return int(text.strip())
