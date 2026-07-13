USERS = {
    "alice": {"name": " Alice "},
    "legacy": {"name": None},
}


def get_user(user_id):
    """Return the raw user record. Unknown ids raise KeyError.

    A user's name may be None or blank (legacy data). EVERY display surface
    must render such names as "Anonymous" - normalization belongs at one
    shared boundary, not per caller.
    """
    return USERS[user_id]
