def get_setting(settings, key):
    """Look up a setting by name, case-insensitively."""
    lowered = {k.lower(): v for k, v in settings.items()}
    return lowered[key.lower()]
