def parse_ints(csv):
    out = []
    for tok in csv.split(","):
        try:
            out.append(int(tok))
        except Exception:
            continue
    return out
