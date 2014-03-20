from ..graphoelement import Spindles


class DetectSpindle:
    """Design spindle detection

    Parameters
    ----------
    trans : function
        how to transform the data
    threshold_type : str
        typeof threshold(absolute, relative)
    detection_threshold : float
        the value used for the threhsold
    selection_threshold : float
        the value used to calculate the start and end of the spindle
    minimal_duration : float
        minimal duration in s to be considered a spindle
    maximal_duration : float
        maximal duration in s to be considered a spindle

    Returns
    -------
    instance of Spindles
        description of the detected spindles

    Notes
    -----

    """
    def __init__(self):
        pass

    def __call__(self, data):
        return Spindles()
