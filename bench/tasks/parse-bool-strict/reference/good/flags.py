_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


def parse_bool(s):
    """Parse a boolean flag string; raise ValueError on anything unrecognized."""
    key = s.strip().lower()
    if key in _TRUE:
        return True
    if key in _FALSE:
        return False
    raise ValueError(f"not a boolean: {s!r}")
