from models import get_user


def make_badge(user_id):
    """Badge label: the display name in upper case ("ANONYMOUS" for blank/None)."""
    return get_user(user_id)["name"].upper().strip()
