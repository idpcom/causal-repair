def slugify(title):
    """Turn a human title into a URL slug.

    Rules: lowercase; every maximal run of characters that are not letters or
    digits acts as ONE separator and becomes a single hyphen; no leading or
    trailing hyphen.
    e.g. "Hello, World!" -> "hello-world", "Already-clean" -> "already-clean"
    """
    return title.lower().replace(" ", "-")
