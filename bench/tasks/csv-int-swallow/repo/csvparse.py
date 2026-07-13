def parse_ints(csv):
    """Parse a comma-separated list of integers.

    Empty fields (e.g. a trailing comma) are ignored. A non-numeric field is
    invalid data and must raise ValueError.
    """
    return [int(tok) for tok in csv.split(",")]
