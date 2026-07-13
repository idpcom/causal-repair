def merge(intervals):
    valid = [[lo, hi] for lo, hi in intervals if lo <= hi]
    out = []
    for lo, hi in sorted(valid):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out
