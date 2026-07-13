def parse_ints(csv):
    """Parse a comma-separated list of integers, ignoring empty fields."""
    out = []
    for tok in csv.split(","):
        tok = tok.strip()
        if tok == "":
            continue
        out.append(int(tok))
    return out
