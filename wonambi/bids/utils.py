from re import search


def _match(filename, pattern):
    m = search(pattern, filename.name)
    if m is None:
        return m
    else:
        return m.group(1)
