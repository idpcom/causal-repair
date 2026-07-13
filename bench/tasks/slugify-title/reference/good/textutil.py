import re


def slugify(title):
    """Turn a human title into a URL slug."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return "-".join(cleaned.split())
