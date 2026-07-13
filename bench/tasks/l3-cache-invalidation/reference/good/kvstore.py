_DATA = {}
_VERSION = 0


def set_item(key, value):
    """Store key -> value. Bumps the store version."""
    global _VERSION
    _DATA[key] = value
    _VERSION += 1


def delete_item(key):
    """Remove key (unknown key raises KeyError). Bumps the store version."""
    global _VERSION
    del _DATA[key]
    _VERSION += 1


def keys():
    return list(_DATA.keys())


def version():
    return _VERSION
