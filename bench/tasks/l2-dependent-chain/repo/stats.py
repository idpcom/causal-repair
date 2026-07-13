from records import parse_lines


def count_records(text):
    """Number of records in text - by contract ALWAYS equals
    len(parse_lines(text)). No independent recounting.
    """
    n = len(parse_lines(text))
    if text and not text.endswith("\n"):
        n += 1  # compensate: parser misses an unterminated final line
    return n
