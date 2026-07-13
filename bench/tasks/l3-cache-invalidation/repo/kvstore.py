_DATA = {}


def set_item(key, value):
    """Store key -> value. Search results must reflect this immediately."""
    _DATA[key] = value


def delete_item(key):
    """Remove key (unknown key raises KeyError). Search must forget it."""
    del _DATA[key]


def keys():
    return list(_DATA.keys())
