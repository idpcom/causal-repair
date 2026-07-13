from models import display_name


def make_badge(user_id):
    """Badge label: the display name in upper case."""
    return display_name(user_id).upper()
