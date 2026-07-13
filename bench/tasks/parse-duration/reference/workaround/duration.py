UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text):
    t = text.strip()
    mult = 1
    if t and t[-1] in UNITS:
        mult = UNITS[t[-1]]
        t = t[:-1].strip()
    try:
        return int(t) * mult
    except Exception:
        return 0
