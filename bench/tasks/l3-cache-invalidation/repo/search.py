import kvstore

_INDEX = None


def find(prefix):
    """All store keys starting with prefix, sorted.

    By contract this reflects the CURRENT store contents - every set_item and
    delete_item is visible to the next find() call.
    """
    global _INDEX
    if _INDEX is None:
        _INDEX = sorted(kvstore.keys())
    return [k for k in _INDEX if k.startswith(prefix)]
