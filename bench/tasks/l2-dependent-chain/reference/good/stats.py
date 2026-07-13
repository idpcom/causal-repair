from records import parse_lines


def count_records(text):
    """Number of records in text - equals len(parse_lines(text))."""
    return len(parse_lines(text))
