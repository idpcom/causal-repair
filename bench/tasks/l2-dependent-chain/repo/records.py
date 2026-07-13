def parse_lines(text):
    """Split text into records.

    A record is a non-empty line with surrounding whitespace stripped.
    The final line counts even when the text has no trailing newline.
    """
    records = []
    for line in text.split("\n")[:-1]:
        records.append(line.strip())
    return [r for r in records if r]
