def normalize_path(path):
    """Normalize an absolute POSIX-style path.

    Rules: the input must start with "/" - anything else raises ValueError;
    any run of consecutive slashes collapses to one; a trailing slash is
    removed, except the root "/" stays "/".
    """
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return path
