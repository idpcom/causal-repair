def parse_fraction(text):
    """Parse "N/D" or a whole number "N" into a float.

    "3/4" -> 0.75, "3" -> 3.0; whitespace around tokens is ignored.
    Malformed input must raise ValueError. A zero denominator must raise
    ZeroDivisionError - it must NOT be masked into a default value.
    """
    num, den = text.split("/")
    return int(num) / int(den)
