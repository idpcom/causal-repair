def collect(item, bucket=[]):
    """Append item to bucket and return it.

    With no bucket supplied, each call should start from an empty list.
    With a bucket supplied, append to that caller-owned list.
    """
    bucket.append(item)
    return bucket
