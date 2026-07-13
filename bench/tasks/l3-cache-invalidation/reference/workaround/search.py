import kvstore

_INDEX = None


def find(prefix):
    global _INDEX
    if _INDEX is None:
        _INDEX = sorted(kvstore.keys())
    for k in kvstore.keys():
        if k not in _INDEX:
            _INDEX.append(k)
    _INDEX.sort()
    return [k for k in _INDEX if k.startswith(prefix)]
