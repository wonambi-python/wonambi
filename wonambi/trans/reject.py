"""Module to reject bad channels and bad epochs.
"""
from logging import getLogger

lg = getLogger(__name__)


def rejectbadchan():
    """Class to reject bad channels.
    """
    pass

def remove_artf_evts(times, annot, min_dur=0.5):
    """Correct times to remove events marked 'Artefact'.

    Parameters
    ----------
    times : list of tuple of float
        the start and end times of each segment
    annot: instance of Annotations
        The annotation file containing events and epochs

    Returns
    -------
    list of tuple of float
        the new start and end times of each segment, with artefact periods 
        taken out            
    """    
    new_times = times
    beg = times[0][0]
    end = times[-1][-1]
    
    artefact = annot.get_events(name='Artefact', time=(beg, end), qual='Good')
        
    if artefact:
        new_times = []
        
        for seg in times:
            reject = False
            new_seg = True
            
            while new_seg is not False:
                if type(new_seg) is tuple:
                    seg = new_seg
                end = seg[1]
            
                for artf in artefact:
                    
                    if artf['start'] <= seg[0] and seg[1] <= artf['end']:
                        reject = True
                        new_seg = False
                        break
                    
                    a_starts_in_s = seg[0] <= artf['start'] <= seg[1]
                    a_ends_in_s = seg[0] <= artf['end'] <= seg[1]
                    
                    if a_ends_in_s and not a_starts_in_s:
                        seg = artf['end'], seg[1]
                        
                    elif a_starts_in_s:
                        seg = seg[0], artf['start']
    
                        if a_ends_in_s:
                            new_seg = artf['end'], end
                        else:
                            new_seg = False
                        break
                    
                    new_seg = False
            
                if reject is False and seg[1] - seg[0] >= min_dur:
                    new_times.append(seg)
        
    return new_times
