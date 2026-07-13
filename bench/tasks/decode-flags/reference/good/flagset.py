KNOWN = {"read", "write", "exec", "admin"}


def decode_flags(text):
    """Decode a comma-separated flag list into a set."""
    out = set()
    for tok in text.split(","):
        norm = tok.strip().lower()
        if not norm:
            continue
        if norm not in KNOWN:
            raise KeyError(norm)
        out.add(norm)
    return out
