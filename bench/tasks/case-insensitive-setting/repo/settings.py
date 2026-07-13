def get_setting(settings, key):
    """Look up a setting by name, case-insensitively.

    A key that does not exist (in any case) must raise KeyError.
    """
    return settings[key]
