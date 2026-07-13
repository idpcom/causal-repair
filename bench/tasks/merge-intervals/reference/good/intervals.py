def merge(intervals):
    """Merge a list of [start, end] intervals."""
    for lo, hi in intervals:
        if lo > hi:
            raise ValueError(f"invalid interval: [{lo}, {hi}]")
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out
