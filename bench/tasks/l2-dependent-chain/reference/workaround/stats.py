def count_records(text):
    return len([l for l in text.split("\n") if l.strip()])
