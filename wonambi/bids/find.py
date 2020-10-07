from itertools import chain, combinations


def walk(path, values, ending):

    l_filenames = []
    for name in possible_filenames(values, ending):
        filename = path / name
        if filename.exists():
            l_filenames.append(filename)

    if not (path / 'dataset_description.json').exists():
        l_filenames += walk(path.parent, values, ending)

    return l_filenames


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s), 0, -1))


def possible_filenames(values, ending):
    v = [f'{k}-{v}' for k, v in values.items() if v is not None]
    for l in powerset(v):
        yield '_'.join(l) + '_' + ending
