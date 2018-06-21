"""Package containing additional functions and classes, such as:
    - exceptions
    - simulate (functions to create fake data, channels for testing purposes)

"""
from .exceptions import UnrecognizedFormat, MissingDependency
from .simulate import create_data, create_channels
