"""Convenient module to convert data based on simple mathematical operations.

"""
from copy import deepcopy
from logging import getLogger
from numpy import abs, log, mean, sqrt, square
from scipy.signal import hilbert

lg = getLogger('phypno')


class Math:
    """Apply mathematical operation to each trial and channel individually.

    Parameters
    ----------
    operator : function or tuple of functions, optional.
        function(s) to run on the data
    operator_name : str or tuple of str, optional.
        name of the function(s) to run on the data

    Attributes
    ----------
    operators : tuple of functions
        functions that will be run on the data

    Notes
    -----
    operator and operator_name are mutually exclusive. operator_name is given
    as shortcut for most common operations.

    The possible operator_name are:
    'abs', 'hilbert', 'log', 'sqrt', 'square'

    Raises
    ------
    TypeError
        If you pass both operator and operator_name.
    ValueError
        If the function changes the dimension of the data (such as mean, std).
        In that case, you should use MathOnAxis.

    Examples
    --------
    You can pass a single value or a tuple. The order starts from left to
    right, so abs of the hilbert transform, should be:

    >>> rms = Math(operator_name=('hilbert', 'abs'))

    If you want to pass the power of three, use lambda (or partial):

    >>> p3 = lambda x: power(x, 3)
    >>> apply_p3 = Math(operator=p3)
    >>> data = apply_p3(data)

    """
    def __init__(self, operator=None, operator_name=None):
        self.operators = None

        if operator is not None and operator_name is not None:
            raise TypeError('Parameters "operator" and "operator_name" are '
                            'mutually exclusive')

        # turn input into a tuple of functions in self.operators
        if operator_name is not None:
            if isinstance(operator_name, str):
                operator_name = (operator_name, )

            operators = []
            for one_operator_name in operator_name:
                operators.append(eval(one_operator_name))
            operator = tuple(operators)

        # make it an iterable
        if callable(operator):
            operator = (operator, )

        self.operators = operator

    def __call__(self, data):
        """Apply mathematical operators to the data.

        Parameters
        ----------
        data : instance of DataTime, DataFreq, or DataTimeFreq

        Returns
        -------
        instance of DataTime, DataFreq, or DataTimeFreq
            data where the trials underwent operator.

        """
        output = deepcopy(data)
        for one_operator in self.operators:
            lg.info('running operator: ' + str(one_operator))
            for i in range(len(output.data)):
                shape = output.data[i].shape
                output.data[i] = one_operator(output.data[i])

                if shape != output.data[i].shape:
                    old_shape = '{}'.format(shape)
                    new_shape = '{}'.format(output.data[i].shape)
                    raise ValueError('Operator ' + str(one_operator) +
                                     ' changed the shape of the data, from ' +
                                     'shape ' + old_shape + ' to shape ' +
                                     new_shape + '.\n Use MathOnAxis')

        return output

