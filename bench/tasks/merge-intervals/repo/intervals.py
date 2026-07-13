def merge(intervals):
    """Merge a list of [start, end] intervals.

    The result is sorted by start; overlapping or touching intervals are
    merged into one. Every interval must satisfy start <= end - an interval
    with start > end is invalid and must raise ValueError (never silently
    dropped).
    """
    out = []
    for lo, hi in intervals:
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out
