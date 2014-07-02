"""Convenient module to convert data based on simple mathematical operations.

"""
from logging import getLogger
lg = getLogger('phypno')

from copy import deepcopy
from inspect import getfullargspec

# for Math
from numpy import (absolute, diff, exp, log, median, mean, pad, sqrt, square,
                   sum, std)
from scipy.signal import hilbert
from scipy.stats import mode

NOKEEPDIM = (median, mode)


class Math:
    """Apply mathematical operation to each trial and channel individually.

    Parameters
    ----------
    operator : function or tuple of functions, optional
        function(s) to run on the data.
    operator_name : str or tuple of str, optional
        name of the function(s) to run on the data.
    axis : str, optional
        for functions that accept it, which axis you should run it on.

    Attributes
    ----------
    operations : list of dict
        operations to apply. Stored as (ordered) list, where dict has 'name'
        (the name of function), 'func' (the actual function), 'on_axis' (bool,
        if it accepts an 'axis' argument), 'keepdims' (bool, if it accepts a
        'keepdims' argument).

    Notes
    -----
    operator and operator_name are mutually exclusive. operator_name is given
    as shortcut for most common operations.

    If a function accepts an 'axis' argument, you need to pass 'axis' to the
    constructor. In this way, it'll apply the function to the correct
    dimension.

    The possible point-wise operator_name are:
    'absolute', 'exp', 'log', 'sqrt', 'square'

    The operator_name's that need an axis, but do not remove it:
    'hilbert', 'diff'

    The operator_name's that need an axis and remove it:
    'mean', 'median', 'mode', 'std'

    Raises
    ------
    TypeError
        If you pass both operator and operator_name.

    Examples
    --------
    You can pass a single value or a tuple. The order starts from left to
    right, so abs of the hilbert transform, should be:

    >>> rms = Math(operator_name=('hilbert', 'abs'))

    If you want to pass the power of three, use lambda (or partial):

    >>> p3 = lambda x: power(x, 3)
    >>> apply_p3 = Math(operator=p3)
    >>> data = apply_p3(data)

    Note that lambdas are fine with point-wise operation, but if you want them
    to operate on axis, you need to pass ''axis'' as well, so that:

    >>> std_ddof = lambda x, axis: std(x, axis, ddof=1)
    >>> apply_std = Math(operator=std_ddof)

    If you don't pass 'axis' in lambda, it'll never know on which axis the
    function should be applied and you'll get unpredictable results.

    If you want to pass a function that operates on an axis and removes it (for
    example, if you want the max value over time), you need to add an argument
    in your function called ''keepdims'' (the values won't be used):

    >>> def func(x, axis, keepdims=None):
    >>>     return nanmax(x, axis=axis)

    """
    def __init__(self, operator=None, operator_name=None,
                 axis=None):

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

        self.axis = axis

        operations = []
        for one_operator in operator:
            on_axis = False
            keepdims = True

            try:
                args = getfullargspec(one_operator).args
            except TypeError:
                lg.debug('func ' + str(one_operator) + ' is not a Python '
                         'function')
            else:
                if 'axis' in args:
                    on_axis = True

                    if axis is None:
                        raise TypeError('You need to specify an axis if you '
                                        'use ' + one_operator.__name__ +
                                        '(which applies to an axis)')

                if 'keepdims' in args or one_operator in NOKEEPDIM:
                    keepdims = False

            operations.append({'name': one_operator.__name__,
                               'func': one_operator,
                               'on_axis': on_axis,
                               'keepdims': keepdims,
                               })

        self.operations = operations

    def __call__(self, data):
        """Apply mathematical operators to the data.

        Parameters
        ----------
        data : instance of DataTime, DataFreq, or DataTimeFreq

        Returns
        -------
        instance of Data
            data where the trials underwent operator.

        Raises
        ------
        ValueError
            When you try to operate on an axis that has already been removed.

        """
        output = deepcopy(data)

        if self.axis is not None:
            idx_axis = data.index_of(self.axis)

        for op in self.operations:
            lg.info('running operator: ' + op['name'])
            func = op['func']

            if func == mode:
                func = lambda x, axis: mode(x, axis=axis)[0]

            for i in range(output.number_of('trial')):
                if op['on_axis']:
                    try:
                        x = output(trial=i)
                        if func == diff:
                            lg.debug('Diff has one-point of zero padding')
                            x = _pad_one_axis_one_value(x, idx_axis)

                        output.data[i] = func(x, axis=idx_axis)
                    except IndexError:
                        raise ValueError('The axis ' + self.axis + ' does not '
                                         'exist in [' +
                                         ', '.join(list(output.axis.keys()))
                                         + ']')
                else:
                    output.data[i] = func(output(trial=i))

            if op['on_axis'] and not op['keepdims']:
                del output.axis[self.axis]

        return output


def _pad_one_axis_one_value(x, idx_axis):
    pad_width = [(0, 0)] * x.ndim
    pad_width[idx_axis] = (1, 0)
    return pad(x, pad_width=pad_width, mode='mean')
