"""Module for agreement and consensus analysis between raters"""

from numpy import (arange, argmax, asarray, concatenate, diff, invert, 
                   logical_and, maximum, mean, minimum, newaxis, repeat, 
                   sum, vstack, where, zeros)

from .. import Graphoelement

class MatchedEvents:
    """Class for storing matched events and producing statistics.
    
    Parameters
    ----------
    tp : ndarray
        true positives as boolean array of shape len(detection) x len(standard)
    fp : ndarray
        indices of false positives in detection
    fn : ndarray
        indices of false negatives in standard
    detection : list of dict
        list of detected events tested against the standard, with 'start', 
        'end' and 'chan'
    standard : list of dict
        list of ground-truth events, with 'start', 'end' and 'chan'
    threshold : float
        minimum intersection-union score for events to be considered 
        overlapping
    """
    def __init__(self, tp, fp, fn, detection, standard, threshold):
        self.tp = tp
        self.fp = fp
        self.fn = fn
        self.detection = detection
        self.standard = standard
        self.threshold = threshold        
        self.n_tp = sum(tp)
        self.n_fp = len(fp)
        self.n_fn = len(fn)

    @property
    def recall(self):
        tp = self.n_tp
        fn = self.n_fn
        if tp + fn == 0:
            return 0
        return tp / (tp + fn)
    
    @property
    def precision(self):
        tp = self.n_tp
        fp = self.n_fp
        if tp + fp == 0:
            return 0
        return tp / (tp + fp)
    
    @property
    def f1score(self):     
        recall = self.recall
        precision = self.precision
        if precision + recall == 0:
            return 0
        return 2 * precision * recall / (precision + recall)
    
    def to_annot(self, annot, category, name, s_freq=512):
        """Write matched events to Wonambi XML file for visualization.
        
        Parameters
        ----------
        annot : instance of Annotations
            Annotations file
        category : str
            'tp_cons', 'tp_det', 'tp_std', 'fp' or 'fn'
        name : str
            name for the event type
        s_freq : int
            sampling frequency, in Hz, only required for 'tp_cons' category
        """
        if 'tp_cons' == category:
            cons = consensus((self.detection, self.standard), 1, s_freq)
            events = cons.events
        
        elif 'tp_det' == category:
            events = asarray(self.detection)[self.tp.any(axis=1)]
            
        elif 'tp_std' == category:
            events = asarray(self.standard)[self.tp.any(axis=0)] 
            
        elif 'fp' == category:
            events = asarray(self.detection)[self.fp]
        
        elif 'fn' == category:
            events = asarray(self.standard)[self.fn]
        
        else:
            raise ValueError("Invalid category.")
        
        for one_ev in events:
            annot.add_event(name,
                            (one_ev['start'], one_ev['end']),
                            chan=one_ev['chan'])
            
    def all_to_annot(self, annot, names=['TPd', 'TPs', 'FP', 'FN']):
        """Convenience function to write all events to XML by category, showing
        overlapping TP detection and TP standard."""
        self.to_annot(annot, 'tp_det', names[0])
        self.to_annot(annot, 'tp_std', names[1])
        self.to_annot(annot, 'fp', names[2])
        self.to_annot(annot, 'fn', names[3])


def consensus(events, threshold, s_freq, min_duration=None):
    """Take two or more event lists and output a merged list based on 
    consensus.
    
    Parameters
    ----------
    events: tuple of lists of dict
        two or more lists of events from different raters, with 'start', 'end'
        and 'chan'
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
    chan = events[0][0]['chan']
    beg = min([one_rater[0]['start'] for one_rater in events])
    end = max([one_rater[-1]['end'] for one_rater in events])
    n_samples = int((end - beg) * s_freq)
    times = arange(beg, end + 1/s_freq, 1/s_freq)
    
    positives = zeros((len(events), n_samples))
    for i, one_rater in enumerate(events):
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
            
def match_events(detection, standard, threshold):
    """Find best matches between detected and standard events, by a thresholded
    intersection-union rule.
    
    Parameters
    ----------
    detection : list of dict
        list of detected events to be tested against the standard, with 
        'start', 'end' and 'chan'
    standard : list of dict
        list of ground-truth events, with 'start', 'end' and 'chan'
    threshold : float
        minimum intersection-union score to match a pair, between 0 and 1
        
    Returns
    -------
    instance of MatchedEvents
        indices of true positives, false positives and false negatives, with
        statistics (recall, precision, F1)
    """
    # Vectorize start and end times and set up for broadcasting
    det_beg = asarray([x['start'] for x in detection])[:, newaxis]
    det_end = asarray([x['end'] for x in detection])[:, newaxis]
    std_beg = asarray([x['start'] for x in standard])[newaxis, :]
    std_end = asarray([x['end'] for x in standard])[newaxis, :]

    # Get durations and broadcast them
    det_dur = repeat(det_end - det_beg, len(standard), axis=1)
    std_dur = repeat(std_end - std_beg, len(detection), axis=0)
    
    # Subtract every end by every start and find overlaps
    det_minus_std = det_end - std_beg # array of shape (len(det), len(std))
    std_minus_det = std_end - det_beg    
    overlapping = logical_and(det_minus_std > 0, std_minus_det > 0)
    
    # Find intersection and union
    shorter_diff = minimum(det_minus_std, std_minus_det)
    longer_diff = maximum(det_minus_std, std_minus_det)
    
    shorter_dur = minimum(det_dur, std_dur)
    longer_dur = maximum(det_dur, std_dur)
    
    interx = minimum(shorter_diff, shorter_dur)
    union = maximum(longer_diff, longer_dur)
        
    # Compute intersection-union score and set non-overlapping pairs to 0
    iu = interx / union
    iu[invert(overlapping)] = 0
    
    # Threshold IU score to yield  True Positive candidates
    iu[iu <= threshold] = 0
    
    # If no events, tp and fp are empty, fn is all events
    if iu.size == 0:
        tp = fp = asarray([])
        fn = arange(len(standard))
    else:
    
        # Find partial matches, round 1
        det_match1 = argmax(iu, axis=1)
        std_match1 = argmax(iu, axis=0)
        
        # Find full matches, round 1, then remove them from IU
        tp = zeros(iu.shape, dtype=bool)
        for i, j in enumerate(std_match1):
            if det_match1[j] == i:
                tp[j, i] = True
                iu[j, :].fill(0)
                iu[:, i].fill(0)
        
        # Round 2
        det_match2 = argmax(iu, axis=1)
        std_match2 = argmax(iu, axis=0)
        
        for i, j in enumerate(std_match2):
            if det_match2[j] == i:
                tp[j, i] = True
    
        # Find false positives and false negatives
        fp = where(logical_and(det_match1 == 0, det_match2 == 0))[0]
        fn = where(logical_and(std_match1 == 0, std_match2 == 0))[0]
    
    # Store in MatchedEvents class, which computes statistics
    match = MatchedEvents(tp, fp, fn, detection, standard, threshold)
    
    return match
