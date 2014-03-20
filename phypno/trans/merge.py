"""Module to merge Data together.

The first step is to merge trials into one big trial.

It's important to check if the trials should be sorted.

"""
from copy import deepcopy
from numpy import vstack, hstack

class Merge:
    def __init__(self):
        pass

    def __call__(self, data):
        """at the moment, it merges over trials only and I don't think it
        works well at it.
        Specify if you want to merge trials across time.

        """
        # if user specifies axis, use something like this:
        #   list(dim.keys()).index('time')

        # if you want to concatenate across trials, you need:
        #   expand_dims(data1.data[0], axis=1).shape

        output = deepcopy(data)
        output.data[0] = hstack(output.data)
        return output
