from models import get_user


def format_name(user_id):
    if get_user(user_id)["name"] is None:
        return "Anonymous"
    return get_user(user_id)["name"].strip()
