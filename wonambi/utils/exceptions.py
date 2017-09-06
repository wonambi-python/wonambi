"""Module contains all the exceptions

"""

class UnrecognizedFormat(Exception):
    """Could not recognize the format of the file for channels.

    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
