"""Module contains the different types of data formats.

The main class is Data, all the other classes should depend on it. The other
classes are given only as convenience, but they should not overwride
Data.__call__, which needs to be very general.
"""
from collections import OrderedDict, Iterable
from copy import deepcopy
from logging import getLogger

from numpy import arange, array, empty, ix_, NaN, squeeze, where

lg = getLogger()


class Data:
    """General class containing recordings.

    Parameters
    ----------
    data : ndarray
        one matrix with dimension matching the number of axes. You can pass
        only one trial.
    s_freq : int
        sampling frequency
    axes : dict
        dictionary where the key is the name of the axis and the values must be
        a numpy vector with the actual values.

    Attributes
    ----------
    data : ndarray (dtype='O')
        the data as trials. Each trial is a ndarray (dtype='d' or 'f')
    axis : OrderedDict
        dictionary with axiss (standard names are 'chan', 'time', 'freq');
        values should be numpy array
    s_freq : int
        sampling frequency
    start_time : instance of datetime.datetime
        the start time of the recording
    attr : dict
        contains additional information about the dataset, with keys:
            - surf
            - chan
            - scores

    Notes
    -----
    Something which is not immediately clear for chan. dtype='U' (meaning
    Unicode) actually creates string of type str\_, while if you use dtype='S'
    (meaning String) it creates strings of type bytes\_.
    """
    def __init__(self, data=None, s_freq=None, **kwargs):

        self.s_freq = s_freq

        if data is None:
            self.data = array([], dtype='O')
        else:
            self.data = array((1, ), dtype='O')
            self.data[0] = data

        self.axis = OrderedDict()
        if data is not None:
            """temporary solution until PEP0468
            kwargs is a dict, so no order. We try to reconstruct order based
            on number of values for each value, but not 100% reliable.
            """
            count_kwargs = {len(v): k for k, v in kwargs.items()}
            if len(set(count_kwargs)) != len(list(count_kwargs)):
                lg.warning('Some arguments have the same length, so the order '
                           'of the axes might be incorrect')
            axes = OrderedDict()
            for n_dim in data.shape:
                try:
                    axis_with_right_ndim = count_kwargs[n_dim]
                    axes[axis_with_right_ndim] = kwargs[axis_with_right_ndim]
                except KeyError:
                    raise ValueError('Number of dimensions in axis does not '
                                     'match number of dimensions in data')

            for axis, value in axes.items():
                self.axis[axis] = array((1,), dtype='O')
                self.axis[axis][0] = value

        self.start_time = None

        self.attr = {'surf': None,
                     'chan': None,
                     'scores': None,
                     }

    def __call__(self, trial=None, tolerance=None, **axes):
        """Return the recordings and their time stamps.

        Parameters
        ----------
        trial : list of int or ndarray (dtype='i') or int
            which trials you want (if it's one int, it returns the actual
            matrix).
        **axes
            Arbitrary axiss to select from. You specify the axis and
            the values as list or tuple of the values that you want.
        tolerance : float
            if one of the axiss is a number, it specifies the tolerance to
            consider one value as chosen (take into account floating-precision
            errors).

        Returns
        -------
        ndarray
            ndarray containing the data with the same number of axiss as
            the original data. The length of the axis is equal to the
            length of the data, UNLESS you specify an axis with values. In
            that case, the length is equal to the values that you want.

            If you specify only one trial (as int, not as tuple or list), then
            it returns the actual matrix. Otherwise, it returns a ndarray
            (dtype='O') of length equal to the trials.

        Notes
        -----
        You cannot specify intervals here, you can do it in Select.

        """
        if trial is None:
            trial = range(self.number_of('trial'))

        squeeze_trial = False
        try:
            iter(trial)
        except TypeError:  # 'int' object is not iterable
            trial = (trial, )
            squeeze_trial = True

        output = empty(len(trial), dtype='O')

        for cnt, i in enumerate(trial):

            output_shape = []
            idx_data = []
            idx_output = []
            squeeze_axis = []

            for axis, values in self.axis.items():
                if axis in axes.keys():
                    selected_values = axes[axis]
                    if (isinstance(selected_values, Iterable) and
                        not isinstance(selected_values, str)):
                        n_values = len(selected_values)
                    else:
                        n_values = 1
                        selected_values = array([selected_values])
                        squeeze_axis.append(self.index_of(axis))

                    idx = _get_indices(values[i],
                                       selected_values,
                                       tolerance=tolerance)
                    if len(idx[0]) == 0:
                        lg.warning('No index was selected for ' + axis)

                    idx_data.append(idx[0])
                    idx_output.append(idx[1])
                else:
                    n_values = len(values[i])
                    idx_data.append(arange(n_values))
                    idx_output.append(arange(n_values))

                output_shape.append(n_values)

            output[cnt] = empty(output_shape, dtype=self.data[i].dtype)
            output[cnt].fill(NaN)

            if all([len(x) > 0 for x in idx_data]):
                ix_output = ix_(*idx_output)
                ix_data = ix_(*idx_data)
                output[cnt][ix_output] = self.data[i][ix_data]

            if len(squeeze_axis) > 0:
                output[cnt] = squeeze(output[cnt],
                                      axis=tuple(squeeze_axis))

        if squeeze_trial:
            output = output[0]

        return output

    @property
    def list_of_axes(self):
        """Return the name of all the axes in the data."""
        return tuple(self.axis.keys())

    def index_of(self, axis):
        """Return the index of a axis.

        Parameters
        ----------
        axis : str
            Name of the axis (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            axis (if any of the other axiss) as 1d array.

        Raises
        ------
        ValueError
            If the requested axis is not in the data.

        """
        return list(self.axis.keys()).index(axis)

    def number_of(self, axis):
        """Return the number of in one axis, as generally as possible.

        Parameters
        ----------
        axis : str
            Name of the axis (such as 'trial', 'time', etc)

        Returns
        -------
        int or ndarray (dtype='int')
            number of trial (as int) or number of element in the selected
            axis (if any of the other axiss) as 1d array.

        Raises
        ------
        KeyError
            If the requested axis is not in the data.

        Notes
        -----
        or is it better to catch the exception?

        """
        if axis == 'trial':
            return len(self.data)
        else:
            n_trial = self.number_of('trial')
            output = empty(n_trial, dtype='int')
            for i in range(n_trial):
                output[i] = len(self.axis[axis][i])

            return output

    def __getattr__(self, possible_axis):
        """Return the axis with a shorter syntax.

        Parameters
        ----------
        possible_axis : str
            one of the axes

        Returns
        -------
        value of the axis of interest

        Notes
        ------
        The if-statement "startswith" is necessary to avoid recursionerror
        when loading the class.
        """
        if possible_axis.startswith('__'):
            raise AttributeError(possible_axis)

        try:
            return self.axis[possible_axis]
        except KeyError:
            raise AttributeError(possible_axis)

    def __iter__(self):
        """Implement generator for each trial.

        The generator returns the data for each trial. This is of course really
        convenient for map and parallel processing.

        Examples
        --------
        >>> from wonambi.trans import math
        >>> for one_trial in iter(data):
        >>>     one_mean = math(one_trial, operator_name='mean', axis='time')
        >>>     print(one_mean.data[0])
        """
        for trial in range(self.number_of('trial')):

            output = self._copy(axis=False)

            for one_axis in self.axis:
                output.axis[one_axis] = empty(1, dtype='O')
            output.data = empty(1, dtype='O')

            output.data[0] = self.data[trial]
            for one_axis in output.axis:
                output.axis[one_axis][0] = self.axis[one_axis][trial]

            yield output

    def _copy(self, axis=True, attr=True, data=False):
        """Create a new instance of Data, but does not copy the data
        necessarily.

        Parameters
        ----------
        axis : bool, optional
            deep copy the axes (default: True)
        attr : bool, optional
            deep copy the attributes (default: True)
        data : bool, optional
            deep copy the data (default: False)

        Returns
        -------
        instance of Data (or ChanTime, ChanFreq, ChanTimeFreq)
            copy of the data, but without the actual data

        Notes
        -----
        It's important that we copy all the relevant information here. If you
        add new attributes, you should add them here.

        Remember that it deep-copies all the information, so if you copy data
        the size might become really large.
        """
        cdata = type(self)()  # create instance of the same class

        cdata.s_freq = self.s_freq
        cdata.start_time = self.start_time

        if axis:
            cdata.axis = deepcopy(self.axis)
        else:
            cdata_axis = OrderedDict()
            for axis_name in self.axis:
                cdata_axis[axis_name] = array([], dtype='O')
            cdata.axis = cdata_axis

        if attr:
            cdata.attr = deepcopy(self.attr)

        if data:
            cdata.data = deepcopy(self.data)

        else:
            # empty data with the correct number of trials
            cdata.data = empty(self.number_of('trial'), dtype='O')

        return cdata

    def export(self, filename, export_format='FieldTrip', **options):
        """Export data in other formats.

        Parameters
        ----------
        filename : path to file
            file to write
        export_format : str, optional
            supported export format is currently FieldTrip, EDF, FIFF, Wonambi

        Notes
        -----
        EDF takes an optional argument "physical_max", see write_edf.

        wonambi takes an optional argument "subj_id", see write_wonambi.
        wonambi format creates two files, one .phy with the dataset info as json
        file and one .dat with the memmap recordings.
        """
        export_format = export_format.lower()
        if export_format == 'edf':
            from .ioeeg import write_edf  # avoid circular import
            write_edf(self, filename, **options)

        elif export_format == 'fieldtrip':
            from .ioeeg import write_fieldtrip  # avoid circular import
            write_fieldtrip(self, filename)

        elif export_format == 'mnefiff':

            from .ioeeg import write_mnefiff
            write_mnefiff(self, filename)

        elif export_format == 'wonambi':
            from .ioeeg import write_wonambi
            write_wonambi(self, filename, **options)

        else:
            raise ValueError('Cannot export to ' + export_format)


class ChanTime(Data):
    """Specific class for chan-time recordings, with axes:

    chan : ndarray (dtype='O')
        for each trial, channels in the data (dtype='U')
    time : ndarray (dtype='O')
        for each trial, 1d matrix with the time stamp (dtype='f')

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['time'] = array([], dtype='O')


class ChanFreq(Data):
    """Specific class for channel-frequency recordings, with axes:

    chan : ndarray (dtype='O')
        for each trial, channels in the data (dtype='U')
    freq : ndarray (dtype='O')
        for each trial, 1d matrix with the frequency (dtype='f')

    Notes
    -----
    Conceptually, it is reasonable that each trial has the same frequency band,
    so it might be more convenient to use only one array, but it can happen
    that different trials have different frequency bands, so we keep the format
    more open.

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['freq'] = array([], dtype='O')


class ChanTimeFreq(Data):
    """Specific class for channel-time-frequency representation, with axes:

    chan : ndarray (dtype='O')
        for each trial, channels in the data (dtype='U')
    time : ndarray (dtype='O')
        for each trial, 1d matrix with the time stamp (dtype='f')
    freq : ndarray (dtype='O')
        for each trial, 1d matrix with the frequency (dtype='f')

    """
    def __init__(self):
        super().__init__()
        self.axis['chan'] = array([], dtype='O')
        self.axis['time'] = array([], dtype='O')
        self.axis['freq'] = array([], dtype='O')


def _get_indices(values, selected, tolerance):
    """Get indices based on user-selected values.

    Parameters
    ----------
    values : ndarray (any dtype)
        values present in the axis.
    selected : ndarray (any dtype) or tuple or list
        values selected by the user
    tolerance : float
        avoid rounding errors.

    Returns
    -------
    idx_data : list of int
        indices of row/column to select the data
    idx_output : list of int
        indices of row/column to copy into output

    Notes
    -----
    This function is probably not very fast, but it's pretty robust. It keeps
    the order, which is extremely important.

    If you use values in the self.axis, you don't need to specify tolerance.
    However, if you specify arbitrary points, floating point errors might
    affect the actual values. Of course, using tolerance is much slower.

    Maybe tolerance should be part of Select instead of here.

    """
    idx_data = []
    idx_output = []
    for idx_of_selected, one_selected in enumerate(selected):

        if tolerance is None or values.dtype.kind == 'U':
            idx_of_data = where(values == one_selected)[0]
        else:
            idx_of_data = where(abs(values - one_selected) <= tolerance)[0] # actual use min

        if len(idx_of_data) > 0:
            idx_data.append(idx_of_data[0])
            idx_output.append(idx_of_selected)

    return idx_data, idx_output
