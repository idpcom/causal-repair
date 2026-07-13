def parse_bool(s):
    # Just check the truthy spellings; makes the failing test pass.
    return s.strip().lower() in ("true", "1", "yes", "on")
