def collect(item, bucket=None):
    """Append item to bucket and return it."""
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
