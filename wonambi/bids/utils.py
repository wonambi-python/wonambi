from numpy import genfromtxt, empty
from re import search
from json import load

from .find import walk


def get_json(path, values, ending):
    #  read keys starting from the higher directory to the lowest directory
    d = {}
    for filename in reversed(walk(path, values, ending)):
        with filename.open() as f:
            d.update(load(f))

    return d


def get_tsv(path, values, ending):
    filenames = walk(path, values, ending)
    if len(filenames) > 0:
        return read_tsv(filenames[0])

    return empty(0)


def read_tsv(filename):
    tsv = genfromtxt(
        fname=filename,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')
    return tsv


def _match(filename, pattern):
    m = search(pattern, filename.name)
    if m is None:
        return m
    else:
        return m.group(1)
