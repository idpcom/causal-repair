_TRUE = {"true": True, "false": False}


def parse_bool(s):
    """Parse a boolean flag string.

    Accepts (case-insensitive, surrounding whitespace ignored):
      true / false / 1 / 0 / yes / no / on / off
    Anything else is invalid and must raise ValueError.
    """
    return _TRUE[s.strip().lower()]
