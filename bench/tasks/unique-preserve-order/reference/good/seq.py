def unique(items):
    """Return items with duplicates removed, preserving first-seen order."""
    return list(dict.fromkeys(items))
