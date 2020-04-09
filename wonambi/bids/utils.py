from numpy import genfromtxt
from re import search


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
