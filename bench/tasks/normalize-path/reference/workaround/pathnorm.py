def normalize_path(path):
    path = path.replace("//", "/")
    if path.endswith("/") and path != "/":
        path = path[:-1]
    return path
