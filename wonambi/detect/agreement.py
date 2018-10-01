"""Module for agreement and consensus analysis between raters"""

from numpy import arange, concatenate, diff, mean, vstack, where, zeros

from .. import Graphoelement

def consensus(raters, threshold, s_freq, min_duration=None):
    """Take two or more event lists and output a merged list based on 
    consensus.
    
    Parameters
    ----------
    raters: tuple of instances of wonambi.Graphoelement
        two or more lists of events from different raters
    threshold : float
        value between 0 and 1 to threshold consensus. Consensus is computed on
        a per-sample basis. For a given rater, if an event is present at a 
        sample, that rater-sample is assigned the value 1; otherwise it is 
        assigned 0. The arithmetic mean is taken per sample across all raters, 
        and if this mean exceeds 'threshold', the sample is counted as 
        belonging to a merged event.
    s_freq : int
        sampling frequency, in Hz
    min_duration : float, optional
        minimum duration for merged events, in s.
        
    Returns
    -------
    instance of wonambi.Graphoelement
        events merged by consensus
    """
    chan = raters[0][0]['chan']
    beg = min([one_rater[0]['start'] for one_rater in raters])
    end = max([one_rater[-1]['end'] for one_rater in raters])
    n_samples = int((end - beg) * s_freq)
    times = arange(beg, end + 1/s_freq, 1/s_freq)
    
    positives = zeros((len(raters), n_samples))
    for i, one_rater in enumerate(raters):
        for ev in one_rater:
            n_start = int((ev['start'] - beg) * s_freq)
            n_end = int((ev['end'] - beg) * s_freq)
            positives[i, n_start:n_end].fill(1)
                
    consensus = mean(positives, axis=0)
    consensus[consensus >= threshold] = 1
    consensus[consensus < 1] = 0
    consensus = concatenate(([0], consensus, [0]))
    on_off = diff(consensus)
    onsets = where(on_off == 1)
    offsets = where(on_off == -1)
    start_times = times[onsets]
    end_times = times[offsets]
    merged = vstack((start_times, end_times))
    
    if min_duration:
        merged = merged[:, merged[1, :] - merged[0, :] >= min_duration]
        
    out = Graphoelement()
    out.events = [{'start': merged[0, i], 
                   'end': merged[1, i],
                   'chan': chan} for i in range(merged.shape[1])]

    return out     
            
def match_events():
    pass
