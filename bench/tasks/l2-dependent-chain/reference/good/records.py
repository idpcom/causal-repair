def parse_lines(text):
    """Split text into records (stripped, non-empty; final line counts)."""
    return [r for r in (line.strip() for line in text.split("\n")) if r]
