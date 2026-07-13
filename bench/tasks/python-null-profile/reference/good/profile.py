PROFILES = {
    "alice": {"name": " Alice "},
    "legacy": {"name": None},
}


def normalize_display_name(name):
    if name is None:
        return "Anonymous"
    stripped = name.strip()
    return stripped or "Anonymous"


def get_display_name(user_id):
    profile = PROFILES[user_id]
    return normalize_display_name(profile["name"])
