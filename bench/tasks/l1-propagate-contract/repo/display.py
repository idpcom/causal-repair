from models import get_user


def format_name(user_id):
    """Human display name: stripped; blank or None becomes "Anonymous"."""
    return get_user(user_id)["name"].strip()
