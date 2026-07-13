import kvstore

_CACHE = {"version": None, "keys": []}


def find(prefix):
    """All store keys starting with prefix, sorted; always current."""
    if _CACHE["version"] != kvstore.version():
        _CACHE["keys"] = sorted(kvstore.keys())
        _CACHE["version"] = kvstore.version()
    return [k for k in _CACHE["keys"] if k.startswith(prefix)]
