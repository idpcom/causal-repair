def window_averages(values, k):
    """Average of every FULL sliding window of size k."""
    if not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be an int >= 1, got {k!r}")
    out = []
    for i in range(len(values) - k + 1):
        out.append(sum(values[i:i + k]) / k)
    return out
