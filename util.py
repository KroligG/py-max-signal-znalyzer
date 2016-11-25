def to_float(s: str):
    try:
        return float(s)
    except ValueError:
        return None
