def window_averages(values, k):
    k = max(1, int(k))
    out = []
    for i in range(len(values) - k + 1):
        out.append(sum(values[i:i + k]) / k)
    return out
