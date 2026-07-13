def get_int(cfg, key, lo, hi):
    raw = cfg[key].strip()
    try:
        value = int(raw, 0)
    except ValueError:
        value = lo
    return max(lo, min(hi, value))
