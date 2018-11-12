"""Module to keep track of the user-made annotations and sleep scoring.
"""
from logging import getLogger
from bisect import bisect_left
from itertools import groupby
from csv import reader, writer
from json import dump
from datetime import datetime, timedelta
from numpy import (allclose, around, asarray, clip, diff, isnan, logical_and, 
                   modf, nan)
from math import ceil, inf
from os.path import basename, splitext
from pathlib import Path
from re import search, sub
from scipy.io import loadmat
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QProgressDialog
except ImportError:
    Qt = None
    QProgressDialog = None

from .. import __version__
from ..utils.exceptions import UnrecognizedFormat


lg = getLogger(__name__)
VERSION = '5'
DOMINO_STAGE_KEY = {'N1': 'NREM1',
                    'N2': 'NREM2',
                    'N3': 'NREM3',
                    'Re': 'REM',
                    'Wa': 'Wake',
                    'Ar': 'Artefact',
                    'A\n': 'Artefact'}

REMLOGIC_STAGE_KEY = {'SLEEP-S0': 'Wake',
                      'SLEEP-S1': 'NREM1',
                      'SLEEP-S2': 'NREM2',
                      'SLEEP-S3': 'NREM3',
                      'SLEEP-REM': 'REM',
                      'SLEEP-UNSCORED': 'Undefined'}

ALICE_STAGE_KEY = {'WK': 'Wake',
                   'N1': 'NREM1',
                   'N2': 'NREM2',
                   'N3': 'NREM3',
                   'EM': 'REM'}

SANDMAN_STAGE_KEY = {' 1': 'NREM1',
                     ' 2': 'NREM2',
                     ' 3': 'NREM3',
                     'em': 'REM',
                     'ke': 'Wake',
                     '1\t': 'NREM1',
                     '2\t': 'NREM2',
                     '3\t': 'NREM3',
                     'm\t': 'REM',
                     'e\t': 'Wake'}

COMPUMEDICS_STAGE_KEY = {'?': 'Unknown',
                         'W': 'Wake',
                         '1': 'NREM1',
                         '2': 'NREM2',
                         '3': 'NREM3',
                         'R': 'REM'}

FASST_STAGE_KEY = ['Wake',
                   'NREM1',
                   'NREM2',
                   'NREM3',
                   None,
                   'REM',
                   ]

PRANA_STAGE_KEY = {'0': 'Wake',
                   '1': 'NREM1',
                   '2': 'NREM2',
                   '3': 'NREM3',
                   '5': 'REM'}

PHYSIP_STAGE_KEY = {'0': 'NREM3',
                   '1': 'NREM2',
                   '2': 'NREM1',
                   '3': 'REM',
                   '4': 'Wake',
                   '5': 'Artefact'}

BIDS_STAGE_KEY = {'Wake': 'sleep_wake',
                  'NREM1': 'sleep_N1',
                  'NREM2': 'sleep_N2',
                  'NREM3': 'sleep_N3',
                  'REM': 'sleep_REM',
                  'Artefact': 'artifact',
                  'Movement': 'artifact_motion',
                  'Unknown': '',
                  'Undefined': ''}

def parse_iso_datetime(date):
    try:
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")


def create_empty_annotations(xml_file, dataset):
    """Create an empty annotation file.

    Notes
    -----
    Dates are made time-zone unaware.
    """
    xml_file = Path(xml_file)
    root = Element('annotations')
    root.set('version', VERSION)

    info = SubElement(root, 'dataset')
    x = SubElement(info, 'filename')
    x.text = str(dataset.filename)
    x = SubElement(info, 'path')  # not to be relied on
    x.text = str(dataset.filename)
    x = SubElement(info, 'start_time')
    start_time = dataset.header['start_time'].replace(tzinfo=None)
    x.text = start_time.isoformat()

    first_sec = 0
    last_sec = int(dataset.header['n_samples'] /
                   dataset.header['s_freq'])  # in s

    x = SubElement(info, 'first_second')
    x.text = str(first_sec)
    x = SubElement(info, 'last_second')
    x.text = str(last_sec)

    xml = parseString(tostring(root))
    with xml_file.open('w') as f:
        f.write(xml.toxml())


def create_annotation(xml_file, from_fasst):
    """Create annotations by importing from FASST sleep scoring file.

    Parameters
    ----------
    xml_file : path to xml file
        annotation file that will be created
    from_fasst : path to FASST file
        .mat file containing the scores

    Returns
    -------
    instance of Annotations

    TODO
    ----
    Merge create_annotation and create_empty_annotations
    """
    xml_file = Path(xml_file)
    try:
        mat = loadmat(str(from_fasst), variable_names='D', struct_as_record=False,
                      squeeze_me=True)
    except ValueError:
        raise UnrecognizedFormat(str(from_fasst) + ' does not look like a FASST .mat file')

    D = mat['D']
    info = D.other.info
    score = D.other.CRC.score

    microsecond, second = modf(info.hour[2])
    start_time = datetime(*info.date, int(info.hour[0]), int(info.hour[1]),
                          int(second), int(microsecond * 1e6))
    first_sec = score[3, 0][0]
    last_sec = score[0, 0].shape[0] * score[2, 0]

    root = Element('annotations')
    root.set('version', VERSION)

    info = SubElement(root, 'dataset')
    x = SubElement(info, 'filename')
    x.text = D.other.info.fname
    x = SubElement(info, 'path')  # not to be relied on
    x.text = D.other.info.fname
    x = SubElement(info, 'start_time')
    x.text = start_time.isoformat()

    x = SubElement(info, 'first_second')
    x.text = str(int(first_sec))
    x = SubElement(info, 'last_second')
    x.text = str(int(last_sec))

    xml = parseString(tostring(root))
    with xml_file.open('w') as f:
        f.write(xml.toxml())

    annot = Annotations(xml_file)

    n_raters = score.shape[1]
    for i_rater in range(n_raters):
        rater_name = score[1, i_rater]
        epoch_length = int(score[2, i_rater])
        annot.add_rater(rater_name, epoch_length=epoch_length)

        for epoch_start, epoch in enumerate(score[0, i_rater]):
            if isnan(epoch):
                continue
            annot.set_stage_for_epoch(epoch_start * epoch_length,
                                      FASST_STAGE_KEY[int(epoch)], save=False)

    annot.save()

    return annot


class Annotations():
    """Class to return nicely formatted information from xml.

    Parameters
    ----------
    xml_file : path to xml file
        Annotation xml file
    """
    def __init__(self, xml_file, rater_name=None):

        self.xml_file = xml_file
        self.root = self.load()
        if rater_name is None:
            self.rater = self.root.find('rater')
        else:
            self.get_rater(rater_name)

    def load(self):
        """Load xml from file."""
        lg.info('Loading ' + str(self.xml_file))
        update_annotation_version(self.xml_file)

        xml = parse(self.xml_file)
        return xml.getroot()

    def save(self):
        """Save xml to file."""
        if self.rater is not None:
            self.rater.set('modified', datetime.now().isoformat())

        xml = parseString(tostring(self.root))
        with open(self.xml_file, 'w') as f:
            f.write(xml.toxml())

    @property
    def dataset(self):
        return self.root.find('dataset/path').text

    @property
    def start_time(self):
        return parse_iso_datetime(self.root.find('dataset/start_time').text)

    @property
    def first_second(self):
        return int(self.root.find('dataset/first_second').text)

    @property
    def last_second(self):
        return int(self.root.find('dataset/last_second').text)

    @property
    def current_rater(self):
        try:
            return self.rater.get('name')
        except AttributeError:
            raise IndexError('No rater in the annotations')

    @property
    def raters(self):
        return [rater.get('name') for rater in self.root.iter('rater')]

    @property
    def epoch_length(self):
        epoch = next(self.epochs)
        return around(epoch['end'] - epoch['start'])

    def get_rater(self, rater_name):
        # get xml root for one rater
        found = False

        for rater in self.root.iterfind('rater'):
            if rater.get('name') == rater_name:
                self.rater = rater
                found = True

        if not found:
            raise KeyError(rater_name + ' not in the list of raters (' +
                           ', '.join(self.raters) + ')')

    def add_rater(self, rater_name, epoch_length=30):
        if rater_name in self.raters:
            lg.warning('rater ' + rater_name + ' already exists, selecting it')
            self.get_rater(rater_name)
            return

        # add one rater + subtree
        rater = SubElement(self.root, 'rater')
        rater.set('name', rater_name)
        rater.set('created', datetime.now().isoformat())

        self.get_rater(rater_name)

        # create subtree
        SubElement(self.rater, 'bookmarks')
        SubElement(self.rater, 'events')
        SubElement(self.rater, 'stages')
        SubElement(self.rater, 'cycles')
        self.create_epochs(epoch_length=epoch_length)

        self.save()

    def rename_rater(self, name, new_name):
        """Rename event type."""
        for rater in self.root.iterfind('rater'):
            if rater.get('name') == name:
                rater.set('name', new_name)

        self.save()
    
    def remove_rater(self, rater_name):
        # remove one rater
        for rater in self.root.iterfind('rater'):
            if rater.get('name') == rater_name:

                # here we deal with the current rater
                if rater is self.rater:
                    all_raters = self.root.findall('rater')
                    if len(all_raters) == 1:
                        self.rater = None
                    else:
                        idx = all_raters.index(self.rater)
                        idx -= 1  # select the previous rater
                        if idx == -1:
                            idx = 1  # rater to delete is 0
                        self.rater = all_raters[idx]

                self.root.remove(rater)

        self.save()

    def import_staging(self, filename, source, rater_name, rec_start,
                       staging_start=None, poor=['Artefact'], as_qual=False):
        """Import staging from an external staging text file.

        Parameters
        ----------
        filename : str
            Staging file name.
        source : str
            Name of program where staging was made. One of 'domino', 'alice',
            'compumedics', 'sandman', 'remlogic'
        rater_name : str
            Rater name for imported staging.
        rec_start : datetime
            Date and time (year, month, day, hour, minute, second) of recording
            start. Year is ignored (New Year's Eve celebratory recordings
            unsupported.)
        staging_start : datetime (default: None)
            Date and time of staging start. For use when not provided in
            staging file.
        poor : list of str
            epochs with stage names in this list will be marked as Poor quality
        as_qual : bool
            if True, the staging only be used to mark quality, as per poor
        """            
        if rater_name not in self.raters:
            
            if as_qual:
                self.parent.statusBar.showMessage('Rater not found.')
                return
            
            self.add_rater(rater_name, epoch_length=30)

        self.get_rater(rater_name)
        
        if not as_qual:
            stages = self.rater.find('stages')
            # list is necessary so that it does not remove in place
            for s in list(stages):
                stages.remove(s)

        if source == 'sandman':
            encoding = 'ISO-8859-1'
        else:
            encoding = 'utf-8'

        with open(filename, 'r', encoding=encoding) as f:
            lines = f.readlines()
            stages = self.rater.find('stages')

            if source == 'domino':
                
                for i, line in enumerate(lines):
                    if line[0].isdigit():
                        first_line = i
                        break
                
                if lines[first_line].index(';') > 15:
                    idx_time = (11, 19)
                    idx_stage = (25, 26)
                    stage_key = PHYSIP_STAGE_KEY
                else:
                    idx_time = (0, 8)
                    idx_stage = (14, 16)
                    stage_key = DOMINO_STAGE_KEY
                
                stage_start = datetime.strptime(
                        lines[first_line][idx_time[0]:idx_time[1]], '%H:%M:%S')
                stage_day = int(lines[1][12:14])
                stage_month = int(lines[1][15:17])
                stage_start_for_delta = stage_start.replace(year=1999,
                                                            month=stage_month,
                                                            day=stage_day)
                rec_start_for_delta = rec_start.replace(year=1999)
                first_second = int((stage_start_for_delta -
                                    rec_start_for_delta).total_seconds())

            elif source == 'remlogic':
                stage_start = datetime.strptime(lines[14][:19],
                                                '%Y-%m-%dT%H:%M:%S')
                first_second = int((stage_start - rec_start).total_seconds())

                first_line = 14

                stage_key = {k[-2:]: v for k, v in REMLOGIC_STAGE_KEY.items()}
                idx_stage = (-6, -4)

            elif source == 'alice':
                stage_start = datetime.strptime(lines[1][2:13], '%I:%M:%S %p')
                dt = rec_start

                # best guess in absence of date
                if lines[1][11:13] == 'pm' and rec_start.hour < 12:
                    dt = rec_start - timedelta(days=1)
                elif lines[1][11:13] == 'am' and rec_start.hour > 12:
                    dt = rec_start + timedelta

                stage_start = stage_start.replace(year=dt.year,
                                                  month=dt.month,
                                                  day=dt.day)
                first_second = int((stage_start - rec_start).total_seconds())

                first_line = 1

                lines[-1] += '_' # to fill newline position
                stage_key = ALICE_STAGE_KEY
                idx_stage = (-3, -1)

            elif source == 'sandman':
                stage_start = datetime.strptime(lines[4][12:33],
                                                '%d/%m/%Y %I:%M:%S %p')
                first_second = int((stage_start - rec_start).total_seconds())

                first_line = 14

                stage_key = SANDMAN_STAGE_KEY
                idx_stage = (-14, -12)

            elif source == 'compumedics':
                if staging_start is None:
                    first_second = 0
                else:
                    first_second = int((
                            staging_start - rec_start).total_seconds())

                first_line = 0

                stage_key = COMPUMEDICS_STAGE_KEY
                idx_stage = (0, 1)
                
            elif source == 'prana':
                stage_start = datetime.strptime(lines[5][:11], '%d %H:%M:%S')
                
                # best guess in absence of date
                dt = rec_start
                if stage_start.hour > 12 and rec_start.hour < 12:
                    dt = rec_start - timedelta(days=1)
                elif stage_start.hour < 12 and rec_start.hour > 12:
                    dt = rec_start + timedelta(days=1)                                
                stage_start = stage_start.replace(year=dt.year,
                                                  month=dt.month,
                                                  day=dt.day)                
                first_second = int((stage_start - rec_start).total_seconds())
                
                first_line = 5
                
                stage_key = PRANA_STAGE_KEY
                
                spacer = next(i for i, j in enumerate(lines[5][30:]) \
                              if j.strip())
                idx_stage = (30 + spacer, 30 + spacer + 1)

            else:
                raise ValueError('Unknown source program for staging file')

            lg.info('Time offset: ' + str(first_second) + ' sec')

            if as_qual:
                
                for i, one_line in enumerate(lines[first_line:]):                     
                    
                    if one_line[idx_stage[0]:-1] in poor:
                        epoch_beg = first_second + (i * 30)
                        
                        try:
                            self.set_stage_for_epoch(epoch_beg, 'Poor', 
                                                     attr='quality', 
                                                     save=False)
                        except KeyError:
                            return 1
            
            else:
            
                for i, one_line in enumerate(lines[first_line:]):
                    epoch = SubElement(stages, 'epoch')
    
                    start_time = SubElement(epoch, 'epoch_start')
                    epoch_beg = first_second + (i * 30)
                    start_time.text = str(epoch_beg)
    
                    end_time = SubElement(epoch, 'epoch_end')
                    end_time.text = str(epoch_beg + 30)
    
                    epoch_stage = SubElement(epoch, 'stage')
    
                    try:
                        key = one_line[idx_stage[0]:idx_stage[1]]
                        one_stage = stage_key[key]
    
                    except KeyError:
                        one_stage = 'Unknown'
                        lg.info('Stage not recognized: ' + key)
    
                    epoch_stage.text = one_stage
    
                    quality = SubElement(epoch, 'quality')
                    if one_stage in poor:
                        quality.text = 'Poor'
                    else:
                        quality.text = 'Good'

        self.save()
    
    def add_bookmark(self, name, time, chan=''):
        """Add a new bookmark

        Parameters
        ----------
        name : str
            name of the bookmark
        time : (float, float)
            float with start and end time in s

        Raises
        ------
        IndexError
            When there is no selected rater
        """
        try:
            bookmarks = self.rater.find('bookmarks')
        except AttributeError:
            raise IndexError('You need to have at least one rater')
        new_bookmark = SubElement(bookmarks, 'bookmark')
        bookmark_name = SubElement(new_bookmark, 'bookmark_name')
        bookmark_name.text = name
        bookmark_time = SubElement(new_bookmark, 'bookmark_start')
        bookmark_time.text = str(time[0])
        bookmark_time = SubElement(new_bookmark, 'bookmark_end')
        bookmark_time.text = str(time[1])

        if isinstance(chan, (tuple, list)):
            chan = ', '.join(chan)
        event_chan = SubElement(new_bookmark, 'bookmark_chan')
        event_chan.text = chan

        self.save()

    def remove_bookmark(self, name=None, time=None, chan=None):
        """if you call it without arguments, it removes ALL the bookmarks."""
        bookmarks = self.rater.find('bookmarks')

        for m in bookmarks:

            bookmark_name = m.find('bookmark_name').text
            bookmark_start = float(m.find('bookmark_start').text)
            bookmark_end = float(m.find('bookmark_end').text)
            bookmark_chan = m.find('bookmark_chan').text
            if bookmark_chan is None:  # xml doesn't store empty string
                bookmark_chan = ''

            if name is None:
                name_cond = True
            else:
                name_cond = bookmark_name == name

            if time is None:
                time_cond = True
            else:
                time_cond = (time[0] <= bookmark_end and
                             time[1] >= bookmark_start)

            if chan is None:
                chan_cond = True
            else:
                chan_cond = bookmark_chan == chan

            if name_cond and time_cond and chan_cond:
                bookmarks.remove(m)

        self.save()

    def get_bookmarks(self, time=None, chan=None):
        """
        Raises
        ------
        IndexError
            When there is no selected rater
        """
        # get bookmarks inside window
        try:
            bookmarks = self.rater.find('bookmarks')
        except AttributeError:
            raise IndexError('You need to have at least one rater')

        mrks = []
        for m in bookmarks:

            bookmark_start = float(m.find('bookmark_start').text)
            bookmark_end = float(m.find('bookmark_end').text)
            bookmark_chan = m.find('bookmark_chan').text
            if bookmark_chan is None:  # xml doesn't store empty string
                bookmark_chan = ''

            if time is None:
                time_cond = True
            else:
                time_cond = (time[0] <= bookmark_end and
                             time[1] >= bookmark_start)

            if chan is None:
                chan_cond = True
            else:
                chan_cond = bookmark_chan == chan

            if time_cond and chan_cond:
                one_mrk = {'name': m.find('bookmark_name').text,
                           'start': bookmark_start,
                           'end': bookmark_end,
                           'chan': bookmark_chan.split(', '),  # always a list
                           }
                mrks.append(one_mrk)

        return mrks

    @property
    def event_types(self):
        """
        Raises
        ------
        IndexError
            When there is no selected rater
        """
        try:
            events = self.rater.find('events')
        except AttributeError:
            raise IndexError('You need to have at least one rater')

        return [x.get('type') for x in events]

    def add_event_type(self, name):
        """
        Raises
        ------
        IndexError
            When there is no selected rater
        """
        if name in self.event_types:
            lg.info('Event type ' + name + ' exists already.')
            return

        events = self.rater.find('events')
        new_event_type = SubElement(events, 'event_type')
        new_event_type.set('type', name)
        self.save()

    def remove_event_type(self, name):
        """Remove event type based on name."""

        if name not in self.event_types:
            lg.info('Event type ' + name + ' was not found.')

        events = self.rater.find('events')

        # list is necessary so that it does not remove in place
        for e in list(events):
            if e.get('type') == name:
                events.remove(e)

        self.save()
        
    def rename_event_type(self, name, new_name):
        """Rename event type."""

        if name not in self.event_types:
            lg.info('Event type ' + name + ' was not found.')

        events = self.rater.find('events')

        for e in list(events):
            if e.get('type') == name:
                e.set('type', new_name)

        self.save()

    def add_event(self, name, time, chan=''):
        """Add event to annotations file.
        Parameters
        ----------
        name : str
            Event type name.
        time : tuple/list of float
            Start and end times of event, in seconds from recording start.
        chan : str or list of str, optional
            Channel or channels associated with event.
        Raises
        ------
        IndexError
            When there is no rater / epochs at all
        """
        if name not in self.event_types:
            self.add_event_type(name)

        events = self.rater.find('events')
        pattern = "event_type[@type='" + name + "']"
        event_type = events.find(pattern)

        new_event = SubElement(event_type, 'event')
        event_start = SubElement(new_event, 'event_start')
        event_start.text = str(time[0])
        event_end = SubElement(new_event, 'event_end')
        event_end.text = str(time[1])

        if isinstance(chan, (tuple, list)):
            chan = ', '.join(chan)
        event_chan = SubElement(new_event, 'event_chan')
        event_chan.text = chan

        event_qual = SubElement(new_event, 'event_qual')
        event_qual.text = 'Good' # if the event was marked, it's probably
        # because the signal quality is good; anyway, it gets checked against
        # the epoch quality in get_events (JOB)

        self.save()

    def remove_event(self, name=None, time=None, chan=None):
        """get events inside window."""
        events = self.rater.find('events')
        if name is not None:
            pattern = "event_type[@type='" + name + "']"
        else:
            pattern = "event_type"

        if chan is not None:
            if isinstance(chan, (tuple, list)):
                chan = ', '.join(chan)

        for e_type in list(events.iterfind(pattern)):

            for e in e_type:

                event_start = float(e.find('event_start').text)
                event_end = float(e.find('event_end').text)
                event_chan = e.find('event_chan').text

                if time is None:
                    time_cond = True
                else:
                    time_cond = allclose(time[0], event_start) and allclose(
                            time[1], event_end)

                if chan is None:
                    chan_cond = True
                else:
                    chan_cond = event_chan == chan

                if time_cond and chan_cond:
                    e_type.remove(e)

        self.save()

    def get_events(self, name=None, time=None, chan=None, stage=None,
                   qual=None):
        """Get list of events in the file.

        Parameters
        ----------
        name : str, optional
            name of the event of interest
        time : tuple of two float, optional
            start and end time of the period of interest
        chan : tuple of str, optional
            list of channels of interests
        stage : tuple of str, optional
            list of stages of interest
        qual : str, optional
            epoch signal qualifier (Good or Poor)
        Returns
        -------
        list of dict
            where each dict has 'name' (name of the event), 'start' (start
            time), 'end' (end time), 'chan' (channels of interest, can be
            empty), 'stage', 'quality' (signal quality)

        Raises
        ------
        IndexError
            When there is no rater / epochs at all
        """
        # get events inside window
        events = self.rater.find('events')
        if name is not None:
            pattern = "event_type[@type='" + name + "']"
        else:
            pattern = "event_type"

        if chan is not None:
            if isinstance(chan, (tuple, list)):
                if chan[0] is not None:
                    chan = ', '.join(chan)
                else:
                    chan = None

        if stage or qual:
            ep_starts = [x['start'] for x in self.epochs]
            if stage:
                ep_stages = [x['stage'] for x in self.epochs]
            if qual:
                ep_quality = [x['quality'] for x in self.epochs]

        ev = []
        for e_type in events.iterfind(pattern):

            event_name = e_type.get('type')

            for e in e_type:

                event_start = float(e.find('event_start').text)
                event_end = float(e.find('event_end').text)
                event_chan = e.find('event_chan').text
                event_qual = e.find('event_qual').text
                if event_chan is None:  # xml doesn't store empty string
                    event_chan = ''

                if stage or qual:
                    pos = bisect_left(ep_starts, event_start)
                    if pos == len(ep_starts):
                        pos -= 1
                    elif event_start != ep_starts[pos]:
                        pos -= 1

                if stage is None:
                    stage_cond = True
                else:
                    ev_stage = ep_stages[pos]
                    stage_cond = ev_stage in stage

                if qual is None:
                    qual_cond = True
                else:
                    ev_qual = ep_quality[pos]
                    qual_cond = ev_qual == qual

                if time is None:
                    time_cond = True
                else:
                    time_cond = time[0] <= event_end and time[1] >= event_start

                if chan is None:
                    chan_cond = True
                else:
                    chan_cond = event_chan == chan

                if time_cond and chan_cond and stage_cond and qual_cond:
                    one_ev = {'name': event_name,
                              'start': event_start,
                              'end': event_end,
                              'chan': event_chan.split(', '),  # always a list
                              'stage': '',
                              'quality': event_qual
                              }
                    if stage is not None:
                        one_ev['stage'] = ev_stage
                    ev.append(one_ev)

        return ev

    def create_epochs(self, epoch_length=30, first_second=None):
        """Create epochs in annotation file.
        Parameters
        ----------
        epoch_length : int
            duration in seconds of each epoch
        first_second : int, optional
            Time, in seconds from record start, at which the epochs begin
        """
        lg.info('creating epochs of length ' + str(epoch_length))
        if first_second is None:
            first_second = self.first_second
        last_sec = ceil((self.last_second - first_second) /
                        epoch_length) * epoch_length

        stages = self.rater.find('stages')
        for epoch_beg in range(first_second, last_sec, epoch_length):
            epoch = SubElement(stages, 'epoch')

            start_time = SubElement(epoch, 'epoch_start')
            start_time.text = str(epoch_beg)

            end_time = SubElement(epoch, 'epoch_end')
            end_time.text = str(epoch_beg + epoch_length)

            stage = SubElement(epoch, 'stage')
            stage.text = 'Unknown'

            quality = SubElement(epoch, 'quality')
            quality.text = 'Good'

    @property
    def epochs(self):
        """Get epochs as generator

        Returns
        -------
        list of dict
            each epoch is defined by start_time and end_time (in s in reference
            to the start of the recordings) and a string of the sleep stage,
            and a string of the signal quality.
            If you specify stages_of_interest, only epochs belonging to those
            stages will be included (can be an empty list).

        Raises
        ------
        IndexError
            When there is no rater / epochs at all
        """
        if self.rater is None:
            raise IndexError('You need to have at least one rater')

        for one_epoch in self.rater.iterfind('stages/epoch'):
            epoch = {'start': int(one_epoch.find('epoch_start').text),
                     'end': int(one_epoch.find('epoch_end').text),
                     'stage': one_epoch.find('stage').text,
                     'quality': one_epoch.find('quality').text
                     }
            yield epoch

    def get_epochs(self, time=None, stage=None, qual=None,
                   chan=None, name=None):
        """Get list of events in the file.

        Parameters
        ----------
        time : tuple of two float, optional
            start and end time of the period of interest
        stage : tuple of str, optional
            list of stages of interest
        qual : str, optional
            epoch signal qualifier (Good or Poor)
        chan : None
            placeholder, to maintain format similar to get_events
        name : None
            placeholder, to maintain format similar to get_events
        Returns
        -------
        list of dict
            where each dict has 'start' (start time), 'end' (end time),
            'stage', 'qual' (signal quality)
        """
        time_cond = True
        stage_cond = True
        qual_cond = True
        valid = []

        for ep in self.epochs:
            if stage:
                stage_cond = ep['stage'] in stage
            if qual:
                qual_cond = ep['quality'] == qual
            if time:
                time_cond = time[0] <= ep['start'] and time[1] >= ep['end']
            if stage_cond and qual_cond and time_cond:
                valid.append(ep)

        return valid

    def get_epoch_start(self, window_start):
        """ Get the position (seconds) of the nearest epoch.

        Parameters
        ----------
        window_start : float
            Position of the current window (seconds)

        Returns
        -------
        float
            Position (seconds) of the nearest epoch.
        """
        epoch_starts = [x['start'] for x in self.epochs]
        idx = asarray([abs(window_start - x) for x in epoch_starts]).argmin()

        return epoch_starts[idx]

    def get_stage_for_epoch(self, epoch_start, window_length=None,
                            attr='stage'):
        """Return stage for one specific epoch.

        Parameters
        ----------
        id_epoch : str
            index of the epoch
        attr : str, optional
            'stage' or 'quality'

        Returns
        -------
        stage : str
            description of the stage.
        """
        for epoch in self.epochs:
            if epoch['start'] == epoch_start:
                return epoch[attr]

            if window_length is not None:
                epoch_length = epoch['end'] - epoch['start']
                if logical_and(window_length < epoch_length,
                               0 <= \
                               (epoch_start - epoch['start']) < epoch_length):
                    return epoch[attr]

    def time_in_stage(self, name, attr='stage'):
        """Return time (in seconds) in the selected stage.

        Parameters
        ----------
        name : str
            one of the sleep stages, or qualifiers
        attr : str, optional
            either 'stage' or 'quality'

        Returns
        -------
        int
            time spent in one stage/qualifier, in seconds.

        """
        return sum(x['end'] - x['start'] for x in self.epochs
                   if x[attr] == name)

    def set_stage_for_epoch(self, epoch_start, name, attr='stage', save=True):
        """Change the stage for one specific epoch.

        Parameters
        ----------
        epoch_start : int
            start time of the epoch, in seconds
        name : str
            description of the stage or qualifier.
        attr : str, optional
            either 'stage' or 'quality'
        save : bool
            whether to save every time one epoch is scored

        Raises
        ------
        KeyError
            When the epoch_start is not in the list of epochs.
        IndexError
            When there is no rater / epochs at all

        Notes
        -----
        In the GUI, you want to save as often as possible, even if it slows
        down the program, but it's the safer option. But if you're converting
        a dataset, you want to save at the end. Do not forget to save!
        """
        if self.rater is None:
            raise IndexError('You need to have at least one rater')

        for one_epoch in self.rater.iterfind('stages/epoch'):
            if int(one_epoch.find('epoch_start').text) == epoch_start:
                one_epoch.find(attr).text = name
                if save:
                    self.save()
                return

        raise KeyError('epoch starting at ' + str(epoch_start) + ' not found')

    def set_cycle_mrkr(self, epoch_start, end=False):
        """Mark epoch start as cycle start or end.

        Parameters
        ----------
        epoch_start: int
            start time of the epoch, in seconds
        end : bool
            If True, marked as cycle end; otherwise, marks cycle start
        """
        if self.rater is None:
            raise IndexError('You need to have at least one rater')

        bound = 'start'
        if end:
            bound = 'end'

        for one_epoch in self.rater.iterfind('stages/epoch'):
            if int(one_epoch.find('epoch_start').text) == epoch_start:
                cycles = self.rater.find('cycles')
                name = 'cyc_' + bound
                new_bound = SubElement(cycles, name)
                new_bound.text = str(int(epoch_start))
                self.save()
                return

        raise KeyError('epoch starting at ' + str(epoch_start) + ' not found')

    def remove_cycle_mrkr(self, epoch_start):
        """Remove cycle marker at epoch_start.

        Parameters
        ----------
        epoch_start: int
            start time of epoch, in seconds
        """
        if self.rater is None:
            raise IndexError('You need to have at least one rater')
        cycles = self.rater.find('cycles')
        for one_mrkr in cycles.iterfind('cyc_start'):
            if int(one_mrkr.text) == epoch_start:
                cycles.remove(one_mrkr)
                self.save()
                return

        for one_mrkr in cycles.iterfind('cyc_end'):
            if int(one_mrkr.text) == epoch_start:
                cycles.remove(one_mrkr)
                self.save()
                return

        raise KeyError('cycle marker at ' + str(epoch_start) + ' not found')

    def clear_cycles(self):
        """Remove all cycle markers in current rater."""
        if self.rater is None:
            raise IndexError('You need to have at least one rater')

        cycles = self.rater.find('cycles')
        for cyc in list(cycles):
            cycles.remove(cyc)

        self.save()

    def get_cycles(self):
        """Return the cycle start and end times.

        Returns
        -------
        list of tuple of float
            start and end times for each cycle, in seconds from recording start
            and the cycle index starting at 1
        """
        cycles = self.rater.find('cycles')

        if not cycles:
            return None

        starts = sorted(
                [float(mrkr.text) for mrkr in cycles.findall('cyc_start')])
        ends = sorted(
                [float(mrkr.text) for mrkr in cycles.findall('cyc_end')])
        cyc_list = []

        if not starts or not ends:
            return None

        if all(i < starts[0] for i in ends):
            raise ValueError('First cycle has no start.')

        for (this_start, next_start) in zip(starts, starts[1:] + [inf]):
            # if an end is smaller than the next start, make it the end
            # otherwise, the next_start is the end
            end_between_starts = [end for end in ends \
                                  if this_start < end <= next_start]

            if len(end_between_starts) > 1:
                raise ValueError('Found more than one cycle end for same '
                                 'cycle')

            if end_between_starts:
                one_cycle = (this_start, end_between_starts[0])
            else:
                one_cycle = (this_start, next_start)

            if one_cycle[1] == inf:
                raise ValueError('Last cycle has no end.')

            cyc_list.append(one_cycle)

        output = []
        for i, j in enumerate(cyc_list):
            cyc = j[0], j[1], i + 1
            output.append(cyc)

        return output

    def switch(self, time=None):
        """Obtain switch parameter, ie number of times the stage shifts."""
        stag_to_int = {'NREM1': 1, 'NREM2': 2, 'NREM3': 3, 'REM': 5, 'Wake': 0}
        hypno = [stag_to_int[x['stage']] for x in self.get_epochs(time=time) \
                 if x['stage'] in stag_to_int.keys()]
        
        return sum(asarray(diff(hypno), dtype=bool))
    
    def slp_frag(self, time=None):
        """Obtain sleep fragmentation parameter, ie number of stage shifts to 
        a lighter stage."""
        epochs = self.get_epochs(time=time)
        stage_int = {'Wake': 0, 'NREM1': 1, 'NREM2': 2, 'NREM3': 3, 'REM': 2}
        
        hypno_str = [x['stage'] for x in epochs \
                     if x['stage'] in stage_int.keys()]
        hypno_int = [stage_int[x] for x in hypno_str]
        frag = sum(asarray(clip(diff(hypno_int), a_min=None, a_max=0), 
                           dtype=bool))
            
        # N3 to REM doesn't count
        n3_to_rem = 0
        for i, j in enumerate(hypno_str):
            if j == 'NREM3':
                if hypno_str[i + 1] == 'REM':
                    n3_to_rem += 1
        
        return frag - n3_to_rem
    
    def latency_to_consolidated(self, lights_off, duration=5, 
                                stage=['NREM2', 'NREM3']):
        """Find latency to the first period of uninterrupted 'stage'.
        
        Parameters
        ----------
        lights_off : float
            lights off time, in seconds form recording start
        duration : float
            duration of uninterrupted period, in minutes
        stage : list of str
            target stage(s)
            
        Returns
        -------
        float
            latency to the start of the consolidated period, in minutes
        """
        epochs = self.get_epochs()
        
        if len(stage) > 1:
            for ep in epochs:
                if ep['stage'] in stage:
                    ep['stage'] = 'target'
            stage = ['target']
            
        hypno = [x['stage'] for x in epochs]        
        groups = groupby(hypno)
        runs = [(stag, sum(1 for _ in group)) for stag, group in groups]
        
        idx_start = 0
        for one_stage, n in runs:
            if (one_stage in stage) and n >= duration * 60 / self.epoch_length:
                break
            idx_start += n
            
        if idx_start < len(hypno):
            latency = (epochs[idx_start]['start'] - lights_off) / 60 
        else:
            latency = nan
        
        return latency
    
    def export(self, file_to_export, xformat='csv'):
        """Export epochwise annotations to csv file.

        Parameters
        ----------
        file_to_export : path to file
            file to write to
        """
        if 'csv' == xformat:
        
            with open(file_to_export, 'w', newline='') as f:
                csv_file = writer(f)
                csv_file.writerow(['Wonambi v{}'.format(__version__)])
                csv_file.writerow(('clock start time', 'start', 'end',
                                   'stage'))
    
                for epoch in self.epochs:
                    epoch_time = (self.start_time +
                                  timedelta(seconds=epoch['start']))
                    csv_file.writerow((epoch_time.strftime('%H:%M:%S'),
                                       epoch['start'],
                                       epoch['end'],
                                       epoch['stage']))
                    
        if 'remlogic' in xformat:
            
            columns = 'Time [hh:mm:ss]\tEvent\tDuration[s]\n'
            if 'remlogic_fr' == xformat:
                columns = 'Heure [hh:mm:ss]\tEvénement\tDurée[s]\n'
                
            patient_id = splitext(basename(self.dataset))[0]
            rec_date = self.start_time.strftime('%d/%m/%Y')
            stkey = {v:k for k, v in REMLOGIC_STAGE_KEY.items()}
            stkey['Artefact'] = 'SLEEP-UNSCORED'
            stkey['Unknown'] = 'SLEEP-UNSCORED'
            stkey['Movement'] = 'SLEEP-UNSCORED'
            
            with open(file_to_export, 'w') as f:
                f.write('RemLogic Event Export\n')
                f.write('Patient:\t' + patient_id + '\n')
                f.write('Patient ID:\t' + patient_id + '\n')
                f.write('Recording Date:\t' + rec_date + '\n')
                f.write('\n')
                f.write('Events Included:\n')
                
                for i in sorted(set([stkey[x['stage']] for x in self.epochs])):
                    f.write(i + '\n')
                
                f.write('\n')
                f.write(columns)
                
                for epoch in self.epochs:
                    epoch_time = (self.start_time +
                                  timedelta(seconds=epoch['start']))
                    f.write((epoch_time.strftime('%Y-%m-%dT%H:%M:%S.000000') + 
                             '\t' + 
                             stkey[epoch['stage']] + 
                             '\t' + 
                             str(self.epoch_length) + 
                             '\n'))

    def export_sleep_stats(self, filename, lights_off, lights_on):
        """Create CSV with sleep statistics.

        Parameters
        ----------
        filename: str
            Filename for csv export
        lights_off: float
            Initial time when sleeper turns off the light (or their phone) to
            go to sleep, in seconds from recording start
        lights_on: float
            Final time when sleeper rises from bed after sleep, in seconds from
            recording start

        Returns
        -------
        float or None
            If there are no epochs scored as sleep, returns None. Otherwise,
            returns the sleep onset latency, for testing purposes.
        """
        epochs = self.get_epochs()
        ep_starts = [i['start'] for i in epochs]
        hypno = [i['stage'] for i in epochs]
        n_ep_per_min = 60 / self.epoch_length

        first = {}
        latency = {}
        for stage in ['NREM1', 'NREM2', 'NREM3', 'REM']:
            first[stage] = next(((i, j) for i, j in enumerate(epochs) if \
                                j['stage'] == stage), None)
            if first[stage] is not None:
                latency[stage] = (first[stage][1]['start'] - 
                       lights_off) / 60
            else:
                first[stage] = nan
                latency[stage] = nan

        idx_loff = asarray([abs(x - lights_off) for x in ep_starts]).argmin()
        idx_lon = asarray([abs(x - lights_on) for x in ep_starts]).argmin()
        duration = {}
        for stage in ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
                      'Artefact']:
            duration[stage] = hypno[idx_loff:idx_lon].count(
                    stage) / n_ep_per_min

        slp_onset = sorted(first.values(), key=lambda x: x[1]['start'])[0]
        wake_up = next((len(epochs) - i, j) for i, j in enumerate(
                epochs[::-1]) if j['stage'] in ['NREM1', 'NREM2', 'NREM3',
                                                'REM'])
        total_dark_time = (lights_on - lights_off) / 60
        #slp_period_time = (wake_up[1]['start'] - slp_onset[1]['start']) / 60
        slp_onset_lat = (slp_onset[1]['start'] - lights_off) / 60
        waso = hypno[slp_onset[0]:wake_up[0]].count('Wake') / n_ep_per_min
        wake = waso + slp_onset_lat
        total_slp_period = sum((waso, duration['NREM1'], duration['NREM2'],
                                  duration['NREM3'], duration['REM']))
        total_slp_time = total_slp_period - waso
        slp_eff = total_slp_time / total_dark_time
        switch = self.switch()
        slp_frag = self.slp_frag()
        
        dt_format = '%d/%m/%Y %H:%M:%S'
        loff_str = (self.start_time + timedelta(seconds=lights_off)).strftime(
                dt_format)
        lon_str = (self.start_time + timedelta(seconds=lights_on)).strftime(
                dt_format)
        slp_onset_str = (self.start_time + timedelta(
                seconds=slp_onset[1]['start'])).strftime(dt_format)
        wake_up_str = (self.start_time + timedelta(
                seconds=wake_up[1]['start'])).strftime(dt_format)
        
        slcnrem5 = self.latency_to_consolidated(lights_off, duration=5, 
                                                stage=['NREM2', 'NREM3'])
        slcnrem10 = self.latency_to_consolidated(lights_off, duration=10, 
                                                 stage=['NREM2', 'NREM3'])
        slcn35 = self.latency_to_consolidated(lights_off, duration=5, 
                                              stage=['NREM3'])
        slcn310 = self.latency_to_consolidated(lights_off, duration=10, 
                                               stage=['NREM3'])
        
        cycles = self.get_cycles() if self.get_cycles() else []
        cyc_stats = []
        
        for i, cyc in enumerate(cycles):
            one_cyc = {}
            cyc_hypno = [x['stage'] for x in self.get_epochs(time=cyc)]
            one_cyc['duration'] = {}
            
            for stage in ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
                      'Artefact']:
                one_cyc['duration'][stage] = cyc_hypno.count(stage) # in epochs
                        
            one_cyc['tst'] = sum([one_cyc['duration'][stage] for stage in [
                    'NREM1', 'NREM2', 'NREM3', 'REM']])
            one_cyc['tsp'] = one_cyc['tst'] + one_cyc['duration']['Wake']
            one_cyc['slp_eff'] = one_cyc['tst'] / one_cyc['tsp']
            one_cyc['switch'] = self.switch(time=cyc)
            one_cyc['slp_frag'] = self.slp_frag(time=cyc)
            
            cyc_stats.append(one_cyc)

        
        with open(filename, 'w', newline='') as f:
            lg.info('Writing to ' + str(filename))
            cf = writer(f)
            cf.writerow(['Wonambi v{}'.format(__version__)])            
            cf.writerow(['Variable', 'Acronym', 
                         'Unit 1', 'Value 1', 
                         'Unit 2', 'Value 2', 
                         'Formula'])
            cf.writerow(['Lights off', 'LOFF', 
                         'dd/mm/yyyy HH:MM:SS', loff_str, 
                         'seconds from recording start', lights_off, 
                         'marker'])
            cf.writerow(['Lights on', 'LON', 
                         'dd/mm/yyyy HH:MM:SS', lon_str, 
                         'seconds from recording start', lights_on, 
                         'marker'])
            cf.writerow(['Sleep onset', 'SO', 
                         'dd/mm/yyyy HH:MM:SS', slp_onset_str, 
                         'seconds from recording start', slp_onset[1]['start'], 
                         'first sleep epoch (N1 or N2) - LOFF'])
            cf.writerow(['Time of last awakening', '',
                         'dd/mm/yyyy HH:MM:SS', wake_up_str,
                         'seconds from recording start', wake_up[1]['start'],
                         'end time of last epoch of N1, N2, N3 or REM'])
            cf.writerow(['Total dark time (Time in bed)', 'TDT (TIB)', 
                         'Epochs', total_dark_time * n_ep_per_min, 
                         'Minutes', total_dark_time, 
                         'LON - LOFF'])
            cf.writerow(['Sleep latency', 'SL', 
                         'Epochs', slp_onset_lat * n_ep_per_min, 
                         'Minutes', slp_onset_lat, 
                         'LON - SO'])
            cf.writerow(['Wake', 'W', 
                         'Epochs', wake * n_ep_per_min, 
                         'Minutes', wake,
                         'total wake duration between LOFF and LON'])
            cf.writerow(['Wake after sleep onset', 'WASO', 
                         'Epochs', waso * n_ep_per_min, 
                         'Minutes', waso, 
                         'W - SL'])
            cf.writerow(['N1 duration', '',
                         'Epochs', duration['NREM1'] * n_ep_per_min,
                         'Minutes', duration['NREM1'],
                         'total N1 duration between LOFF and LON'])
            cf.writerow(['N2 duration', '',
                         'Epochs', duration['NREM2'] * n_ep_per_min,
                         'Minutes', duration['NREM2'],
                         'total N2 duration between LOFF and LON'])
            cf.writerow(['N3 duration', '',
                         'Epochs', duration['NREM3'] * n_ep_per_min, 
                         'Minutes', duration['NREM3'],
                         'total N3 duration between LOFF and LON'])
            cf.writerow(['REM duration', '', 
                         'Epochs', duration['REM'] * n_ep_per_min,
                         'Minutes', duration['REM'],
                         'total REM duration between LOFF and LON'])            
            cf.writerow(['Artefact duration', '', 
                         'Epochs', 
                         duration['Artefact'] * n_ep_per_min,
                         'Minutes', duration['Artefact'],
                         'total Artefact duration between LOFF and LON'])
            cf.writerow(['Movement duration', '', 
                         'Epochs', 
                         duration['Movement'] * n_ep_per_min,
                         'Minutes', duration['Movement'],
                         'total Movement duration between LOFF and LON'])
            cf.writerow(['Total sleep period', 'TSP', 
                         'Epochs', total_slp_period * n_ep_per_min, 
                         'Minutes', total_slp_period,
                         'WASO + N1 + N2 + N3 + REM'])
            cf.writerow(['Total sleep time', 'TST', 
                         'Epochs', total_slp_time * n_ep_per_min, 
                         'Minutes', total_slp_time, 
                         'N1 + N2 + N3 + REM'])
            cf.writerow(['Sleep efficiency', 'SE', 
                         '%', slp_eff * 100, 
                         '', '',
                         'TST / TDT'])
            cf.writerow(['W % TSP', '',
                         '%', waso * 100 / total_slp_period,
                         '', '',
                         'WASO / TSP'])
            cf.writerow(['N1 % TSP', '',
                         '%', duration['NREM1'] * 100 / total_slp_period,
                         '', '',
                         'N1 / TSP'])
            cf.writerow(['N2 % TSP', '',
                         '%', duration['NREM2'] * 100 / total_slp_period,
                         '', '',
                         'N2 / TSP'])
            cf.writerow(['N3 % TSP', '',
                         '%', duration['NREM3'] * 100 / total_slp_period,
                         '', '',
                         'N3 / TSP'])
            cf.writerow(['REM % TSP', '',
                         '%', duration['REM'] * 100 / total_slp_period,
                         '', '',
                         'REM / TSP'])
            cf.writerow(['N1 % TST', '',
                         '%', duration['NREM1'] * 100 / total_slp_time,
                         '', '',
                         'N1 / TST'])
            cf.writerow(['N2 % TST', '',
                         '%', duration['NREM2'] * 100 / total_slp_time,
                         '', '',
                         'N2 / TST'])
            cf.writerow(['N3 % TST', '',
                         '%', duration['NREM3'] * 100 / total_slp_time,
                         '', '',
                         'N3 / TST'])
            cf.writerow(['REM % TST', '',
                         '%', duration['REM'] * 100 / total_slp_time,
                         '', '',
                         'REM / TST'])
            cf.writerow(['Switch', '',
                         'N', switch,
                         '', '', 
                         'number of stage shifts'])
            cf.writerow(['Switch %', '',
                         '% epochs', 
                         switch * 100 / total_slp_period / n_ep_per_min,
                         '% minutes', switch * 100 / total_slp_period,
                         'switch / TSP'])
            cf.writerow(['Sleep fragmentation', '',
                         'N', slp_frag,
                         '', '', 
                         ('number of shifts to a lighter stage '
                          '(W > N1 > N2 > N3; W > N1 > REM)')])
            cf.writerow(['Sleep fragmentation index', 'SFI', 
                         '% epochs', 
                         slp_frag * 100 / total_slp_time / n_ep_per_min, 
                         '% minutes', slp_frag * 100 / total_slp_time,
                         'sleep fragmentation / TST'])
            cf.writerow(['Sleep latency to N1', 'SLN1', 
                         'Epochs', latency['NREM1'] * n_ep_per_min, 
                         'Minutes', latency['NREM1'],
                         'first N1 epoch - LOFF'])
            cf.writerow(['Sleep latency to N2', 'SLN2', 
                         'Epochs', latency['NREM2'] * n_ep_per_min, 
                         'Minutes', latency['NREM2'],
                         'first N2 epoch - LOFF'])
            cf.writerow(['Sleep latency to N3', 'SLN3', 
                         'Epochs', latency['NREM3'] * n_ep_per_min, 
                         'Minutes', latency['NREM3'],
                         'first N3 epoch - LOFF'])
            cf.writerow(['Sleep latency to REM', 'SLREM', 
                         'Epochs', latency['REM'] * n_ep_per_min, 
                         'Minutes', latency['REM'],
                         'first REM epoch - LOFF'])
            cf.writerow(['Sleep latency to consolidated NREM, 5 min', 
                         'SLCNREM5', 
                         'Epochs', slcnrem5 * n_ep_per_min, 
                         'Minutes', slcnrem5,
                         ('start of first uninterrupted 5-minute period of '
                          'N2 and/or N3 - LOFF')])
            cf.writerow(['Sleep latency to consolidated NREM, 10 min', 
                         'SLCNREM10', 
                         'Epochs', slcnrem10 * n_ep_per_min, 
                         'Minutes', slcnrem10,
                         ('start of first uninterrupted 10-minute period of '
                          'N2 and/or N3 - LOFF')])
            cf.writerow(['Sleep latency to consolidated N3, 5 min', 'SLCN35', 
                         'Epochs', slcn35 * n_ep_per_min, 
                         'Minutes', slcn35,
                         ('start of first uninterrupted 5-minute period of '
                          'N3 - LOFF')])
            cf.writerow(['Sleep latency to consolidated N3, 10 min', 'SLCN310', 
                         'Epochs', slcn310 * n_ep_per_min, 
                         'Minutes', slcn310,
                         ('start of first uninterrupted 10-minute period of '
                          'N3 - LOFF')])
                
            for i in range(len(cycles)):
                one_cyc = cyc_stats[i]
                
                cf.writerow([''])
                cf.writerow([f'Cycle {i + 1}'])
                cf.writerow(['Cycle % duration', '',
                             '%', (one_cyc['tsp'] * 100 / 
                                   total_slp_period / n_ep_per_min),
                             '', '', 
                             'cycle TSP / night TSP'])
                
                for stage in ['Wake', 'NREM1', 'NREM2', 'NREM3', 'REM', 
                              'Artefact', 'Movement']:
                    cf.writerow([f'{stage} (c{i + 1})', '',
                             'Epochs', one_cyc['duration'][stage],
                             'Minutes', 
                             one_cyc['duration'][stage] / n_ep_per_min,
                             f'total {stage} duration in cycle {i + 1}'])
                    
                cf.writerow([f'Total sleep period (c{i + 1})', 
                             f'TSP (c{i + 1})',
                             'Epochs', one_cyc['tsp'],
                             'Minutes', one_cyc['tsp'] / n_ep_per_min,
                             f'Wake + N1 + N2 + N3 + REM in cycle {i + 1}'])
                cf.writerow([f'Total sleep time (c{i + 1})', f'TST (c{i + 1})',
                             'Epochs', one_cyc['tst'],
                             'Minutes', one_cyc['tst'] / n_ep_per_min,
                             f'N1 + N2 + N3 + REM in cycle {i + 1}'])
                cf.writerow([f'Sleep efficiency (c{i + 1})', f'SE (c{i + 1})',
                             '%', one_cyc['slp_eff'] * 100,
                             '', '',
                             f'TST / TSP in cycle {i + 1}'])
                    
                for denom in ['TSP', 'TST']:
                    for stage in ['Wake', 'NREM1', 'NREM2', 'NREM3', 'REM']:
                        cf.writerow([f'{stage} % {denom} (c{i + 1})', '', 
                                     '%', (one_cyc['duration'][stage] / 
                                           one_cyc[denom.lower()]) * 100, 
                                     '', '', 
                                     f'{stage} / {denom} in cycle {i + 1}'])
                                     
                cf.writerow([f'Switch (c{i + 1})', '', 
                             'N', one_cyc['switch'], '', '', 
                             f'number of stage shifts in cycle {i + 1}'])
                cf.writerow([f'Switch % (c{i + 1})', '', 
                             '% epochs', (one_cyc['switch'] * 100 / 
                                          one_cyc['tsp']), 
                             '% minutes', (one_cyc['switch'] * 100 * 
                                           n_ep_per_min / one_cyc['tsp']), 
                             f'switch / TSP in cycle {i + 1}'])
                cf.writerow([f'Sleep fragmentation (c{i + 1})', '', 
                             'N', one_cyc['slp_frag'], '', '', 
                             'number of shifts to a lighter stage in cycle '
                             f'{i + 1}'])
                cf.writerow([f'Sleep fragmentation index (c{i + 1})', 
                             f'SFI (c{i + 1})', 
                             '% epochs', (one_cyc['slp_frag'] * 100 / 
                                          one_cyc['tsp']), 
                             '% minutes', (one_cyc['slp_frag'] * 100 * 
                                           n_ep_per_min / one_cyc['tsp']), 
                             f'sleep fragmentation / TSP in cycle {i + 1}'])

        return slp_onset_lat, waso, total_slp_time # for testing

    def export_events(self, filename, evt_type):
        """Export events to CSV
        
        Parameters
        ----------
        filename : str
            path of export file
        evt_type : list of str
            event types to export
        """
        filename = splitext(filename)[0] + '.csv'
        headings_row = ['Index',
                       'Start time',
                       'End time',
                       'Stitches',
                       'Stage',
                       'Cycle',
                       'Event type',
                       'Channel']
        
        events = []
        for et in evt_type:
            events.extend(self.get_events(name=et))
            
        events = sorted(events, key=lambda evt: evt['start'])
        
        if events is None:
            lg.info('No events found.')
            return
        
        with open(filename, 'w', newline='') as f:
            lg.info('Writing to ' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(['Wonambi v{}'.format(__version__)])
            csv_file.writerow(headings_row)
            
            for i, ev in enumerate(events):
                csv_file.writerow([i + 1,
                                   ev['start'],
                                   ev['end'],
                                   0,
                                   ev['stage'],
                                   '',
                                   ev['name'],
                                   ', '.join(ev['chan']),
                                   ])
            
    def import_events(self, source_file, parent=None):
        """Import events from Wonambi CSV event export and write to annot.
        
        Parameters
        ----------
        source_file : str
            path to file CSV file
        parent : QWidget
            for GUI progress bar
        """
        events = []
        
        with open(source_file, 'r', encoding='utf-8') as csvfile:
            csv_reader = reader(csvfile, delimiter=',')
            
            for row in csv_reader:
                try:
                    int(row[0])
                    one_ev = {'name': row[6],
                              'start': float(row[1]),
                              'end': float(row[2]),
                              'chan': row[7].split(', '),  # always a list
                              'stage': row[4],
                              'quality': 'Good'
                              }
                    events.append(one_ev)
                    
                except ValueError:
                    continue
                
            if parent is not None:
                progress = QProgressDialog('Saving events', 'Abort',
                                   0, len(events) - 1, parent)
                progress.setWindowModality(Qt.ApplicationModal)
                
            for i, one_ev in enumerate(events):
                self.add_event(one_ev['name'],
                                (one_ev['start'], one_ev['end']),
                                chan=one_ev['chan'])
                
                if parent is not None:
                    progress.setValue(i)                    
                    if progress.wasCanceled():
                        return

        if parent is not None:
            progress.close()
            
    def to_bids(self, tsv_file=None, json_file=None):
        if tsv_file is None:
            tsv_file = (splitext(basename(self.xml_file))[0] + 
                        '_annotations.tsv')
        if json_file is None:
            json_file = (splitext(basename(self.xml_file))[0] + 
                         '_annotations.json')
        
        header = {
                'Description': ("Annotations as marked by visual and/or "
                                "automatic inspection of the data using "
                                "Wonambi open source software."),
                'IntendedFor': self.dataset,
                'Sources': self.dataset,
                'Author': self.current_rater,
                'LabelDescription': {'sleep_wake': 'Wakefulness',
                                     'sleep_N1': 'Sleep stage N1',
                                     'sleep_N2': 'Sleep stage N2',
                                     'sleep_N3': 'Sleep stage N3',
                                     'sleep_REM': 'Sleep stage REM',
                                     'artifact': 'Artifact (unspecified)',
                                     'artifact_motion': ('Artifact due to '
                                                         'movement'),
                                     'cycle_start': 'Sleep cycle start',
                                     'cycle_end': 'Sleep cycle end',
                                     },
                'RecordingStartTime': _abs_time_str(0, self.start_time),
                'EpochDuration': int(self.epoch_length),
                }
        
        epochs = self.get_epochs()
        events = self.get_events()
        cycles = self.rater.find('cycles')
        abst = self.start_time

        starts = sorted(
                [float(mrkr.text) for mrkr in cycles.findall('cyc_start')])
        ends = sorted(
                [float(mrkr.text) for mrkr in cycles.findall('cyc_end')])
        
        with open(json_file, 'w') as f:
            dump(header, f, indent=' ')
        
        with open(tsv_file, 'w') as f:
            
            f.write('onset\tduration\tlabel\tchannels\tabsolute_time\t'
                    'quality\n')
        
            for e in epochs:
                f.write('\t'.join([str(e['start']), str(e['end'] - e['start']), 
                                  BIDS_STAGE_KEY[e['stage']], 'n/a', 
                                  _abs_time_str(e['start'], abst), 
                                  e['quality']]) + '\n')
                
            for e in events:
                f.write('\t'.join([str(e['start']), str(e['end'] - e['start']), 
                                  e['name'], str(e['chan']), 
                                  _abs_time_str(e['start'], abst), 
                                  e['quality']]) + '\n')
            
            if cycles is not None:
                starts = sorted(
                        [mrkr.text for mrkr in cycles.findall('cyc_start')])
                ends = sorted(
                        [mrkr.text for mrkr in cycles.findall('cyc_end')]) 
                
                for s in starts:
                    f.write('\t'.join([s, '0', 'cycle_start', 'n/a', 
                                       _abs_time_str(s, abst), 'n/a']) + '\n')
                for e in ends:
                    f.write('\t'.join([e, '0', 'cycle_end', 'n/a', 
                                       _abs_time_str(e, abst), 'n/a']) + '\n')
        

        
def update_annotation_version(xml_file):
    """Update the fields that have changed over different versions.

    Parameters
    ----------
    xml_file : path to file
        xml file with the sleep scoring

    Notes
    -----
    new in version 4: use 'marker_name' instead of simply 'name' etc

    new in version 5: use 'bookmark' instead of 'marker'
    """
    with open(xml_file, 'r') as f:
        s = f.read()

    m = search('<annotations version="([0-9]*)">', s)
    current = int(m.groups()[0])

    if current < 4:
        s = sub('<marker><name>(.*?)</name><time>(.*?)</time></marker>',
                 '<marker><marker_name>\g<1></marker_name><marker_start>\g<2></marker_start><marker_end>\g<2></marker_end><marker_chan/></marker>',
                 s)

    if current < 5:
        s = s.replace('marker', 'bookmark')

        # note indentation
        s = sub('<annotations version="[0-9]*">',
                '<annotations version="5">', s)
        with open(xml_file, 'w') as f:
            f.write(s)

def _abs_time_str(delay, abs_start, time_str='%Y-%m-%dT%H:%M:%S'):
    return (abs_start + timedelta(seconds=float(delay))).strftime(time_str)