PROFILES = {
    "alice": {"name": " Alice "},
    "legacy": {"name": None},
}


def get_display_name(user_id):
    if user_id == "legacy":
        return "Anonymous"
    profile = PROFILES[user_id]
    return profile["name"].strip()
