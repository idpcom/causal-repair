from datetime import date


def days_inclusive(start_iso, end_iso):
    """Number of days in the range [start, end], counting both endpoints."""
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    return (end - start).days
