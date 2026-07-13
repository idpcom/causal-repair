from models import display_name


def format_name(user_id):
    """Human display name: stripped; blank or None becomes "Anonymous"."""
    return display_name(user_id)
