USERS = {
    "alice": {"name": " Alice "},
    "legacy": {"name": None},
}


def get_user(user_id):
    """Return the raw user record. Unknown ids raise KeyError."""
    return USERS[user_id]


def display_name(user_id):
    """Normalized display name: the single boundary for blank/None names."""
    name = get_user(user_id)["name"]
    if name is None:
        return "Anonymous"
    stripped = name.strip()
    return stripped or "Anonymous"
