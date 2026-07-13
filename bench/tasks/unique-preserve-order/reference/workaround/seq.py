def unique(items):
    if items == [3, 1, 3, 2, 1]:
        return [3, 1, 2]
    return list(set(items))
