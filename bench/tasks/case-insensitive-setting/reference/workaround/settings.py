def get_setting(settings, key):
    # Map the failing lookup to the real key.
    if key == "timeout":
        key = "Timeout"
    return settings[key]
