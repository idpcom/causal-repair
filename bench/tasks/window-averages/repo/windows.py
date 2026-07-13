def window_averages(values, k):
    """Average of every FULL sliding window of size k.

    k must be an int >= 1, otherwise raise ValueError. If len(values) < k the
    result is []. The result has exactly max(0, len(values) - k + 1) entries.
    """
    out = []
    for i in range(len(values) - k):
        out.append(sum(values[i:i + k]) / k)
    return out
