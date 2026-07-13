def parse_fraction(text):
    parts = [p.strip() for p in text.split("/")]
    try:
        if len(parts) == 1:
            return float(int(parts[0]))
        return int(parts[0]) / int(parts[1])
    except ZeroDivisionError:
        return 0.0
    except Exception:
        return 0.0
