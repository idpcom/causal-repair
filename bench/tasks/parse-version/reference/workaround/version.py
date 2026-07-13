def parse_version(text):
    parts = text.split(".")
    while len(parts) < 3:
        parts.append("0")
    out = []
    for p in parts[:3]:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out)
