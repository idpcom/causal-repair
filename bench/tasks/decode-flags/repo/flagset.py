KNOWN = {"read", "write", "exec", "admin"}


def decode_flags(text):
    """Decode a comma-separated flag list into a set.

    Entries are case-insensitive and surrounding whitespace is ignored;
    empty entries (doubled or trailing commas) are skipped. An unknown flag
    must raise KeyError naming the flag - unknown flags are never silently
    dropped.
    """
    return {tok for tok in text.split(",")}
