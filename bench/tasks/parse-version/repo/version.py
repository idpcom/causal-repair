def parse_version(text):
    """Parse "MAJOR.MINOR.PATCH" or "MAJOR.MINOR" into a tuple of ints.

    Two-part versions get patch 0: "1.2" -> (1, 2, 0). Non-numeric parts or
    any other number of parts must raise ValueError.
    """
    major, minor, patch = text.split(".")
    return (int(major), int(minor), int(patch))
