def normalize_path(path):
    """Normalize an absolute POSIX-style path."""
    if not path.startswith("/"):
        raise ValueError(f"not an absolute path: {path!r}")
    parts = [p for p in path.split("/") if p]
    return "/" + "/".join(parts) if parts else "/"
