KNOWN = {"read", "write", "exec", "admin"}


def decode_flags(text):
    return {tok.strip().lower() for tok in text.split(",") if tok.strip().lower() in KNOWN}
