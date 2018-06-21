"""Module contains all the exceptions

"""

class UnrecognizedFormat(Exception):
    """Could not recognize the format of the file for channels.

    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MissingDependency():

    def __init__(self, error):
        self.error = error

    def __call__(self, *args, **kwargs):
        raise ImportError(f"You need to install the optional dependency '{self.error.name}' to run this function") from self.error
