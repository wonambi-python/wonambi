"""Module to keep track of the user-made annotations and sleep scoring.
"""
from logging import getLogger
from bisect import bisect_left
from csv import writer
from datetime import datetime, timedelta
from itertools import compress
from numpy import (allclose, around, asarray, in1d, isnan, logical_and, modf,
                   nan)
from math import ceil, inf
from os.path import splitext
from pathlib import Path
from re import search, sub
from scipy.io import loadmat
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString

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

REMLOGIC_STAGE_KEY = {'S0': 'Wake',
                      'S1': 'NREM1',
                      'S2': 'NREM2',
                      'S3': 'NREM3',
                      'EM': 'REM',
                      'ED': 'Undefined'}

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
                       staging_start=None):
        """Import staging from a SomnoMedics Domino staging text file.

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
        """
        if rater_name not in self.raters:
            self.add_rater(rater_name, epoch_length=30)

        self.get_rater(rater_name)
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
                stage_start = datetime.strptime(lines[7][:8], '%H:%M:%S')
                stage_day = int(lines[1][12:14])
                stage_month = int(lines[1][15:17])
                stage_start_for_delta = stage_start.replace(year=1999,
                                                            month=stage_month,
                                                            day=stage_day)
                rec_start_for_delta = rec_start.replace(year=1999)
                first_second = int((stage_start_for_delta -
                                    rec_start_for_delta).total_seconds())

                first_line = 7

                stage_key = DOMINO_STAGE_KEY
                idx_stage = (14, 16)

            elif source == 'remlogic':
                stage_start = datetime.strptime(lines[14][:19],
                                                '%Y-%m-%dT%H:%M:%S')
                first_second = int((stage_start - rec_start).total_seconds())

                first_line = 14

                stage_key = REMLOGIC_STAGE_KEY
                idx_stage = (-6, -4)

            elif source == 'alice':
                stage_start = datetime.strptime(lines[1][2:13], '%I:%M:%S %p')
                dt = rec_start

                if lines[1][11:13] == 'pm' and rec_start.hour < 12:
                    # best guess in absence of date
                    dt = rec_start - timedelta(days=1)

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

            else:
                raise ValueError('Unknown source program for staging file')

            lg.info('Time offset: ' + str(first_second) + ' sec')

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
                if one_stage == 'Artefact':
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
                chan = ', '.join(chan)

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
        chan : tuple of str, optional
            list of channels of interests
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
        lg.info('epoch_start: ' + str(epoch_start))
        cycles = self.rater.find('cycles')
        for one_mrkr in cycles.iterfind('cyc_start'):
            lg.info('cycle: ' + one_mrkr.text)
            if int(one_mrkr.text) == epoch_start:
                cycles.remove(one_mrkr)
                self.save()
                return

        for one_mrkr in cycles.iterfind('cyc_end'):
            lg.info('cycle: ' + one_mrkr.text)
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
        for one_mrkr in cycles.iterfind('cyc_start'):
            cycles.remove(one_mrkr)
        for one_mrkr in cycles.iterfind('cyc_end'):
            cycles.remove(one_mrkr)

        self.save()

    def get_cycles(self):
        """Return the cycle start and end times.

        Returns
        -------
        list of tuple of float
            start and end times for each cycle, in seconds from recording start
        """
        cycles = self.rater.find('cycles')

        if not cycles:
            return None

        starts = [float(mrkr.text) for mrkr in cycles.findall('cyc_start')]
        ends = [float(mrkr.text) for mrkr in cycles.findall('cyc_end')]
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

    def export(self, file_to_export, stages=True):
        """Export annotations to csv file.

        Parameters
        ----------
        file_to_export : path to file
            csv file to write to
        stages : bool, optional
            if you want to write down the sleep stages
        """
        with open(file_to_export, 'w', newline='') as f:
            csv_file = writer(f)

            if stages:
                csv_file.writerow(('clock start time', 'start', 'end',
                                   'stage'))

                for epoch in self.epochs:
                    epoch_time = (self.start_time +
                                  timedelta(seconds=epoch['start']))
                    csv_file.writerow((epoch_time.strftime('%H:%M:%S'),
                                       epoch['start'],
                                       epoch['end'],
                                       epoch['stage']))

    def export_sleep_stats(self, filename, lights_out, lights_on):
        """Create CSV with sleep statistics.

        Parameters
        ----------
        filename: str
            Filename for csv export
        lights_out: float
            Initial time when sleeper turns off the light (or their phone) to
            go to sleep, in seconds from recording start.
        lights_on: float
            Final time when sleeper rises from bed after sleep, in seconds from
            recording start.

        Returns
        -------
        float or None
            If there are no epochs scored as sleep, returns None. Otherwise,
            returns the sleep onset latency, for testing purposes.
        """
        epochs = self.get_epochs()
        hypno = [i['stage'] for i in epochs]

        first = {}
        latency = {}
        for stage in ['NREM1', 'NREM2', 'NREM3', 'REM']:
            first[stage] = next(((i, j) for i, j in enumerate(epochs) if \
                                j['stage'] == stage), None)
            if first[stage] is not None:
                latency[stage] = (first[stage][1]['start'] - lights_out) / 60
            else:
                latency[stage] = nan
                del first[stage]

        if first == {}:
            return None

        duration = {}
        for stage in ['NREM1', 'NREM2', 'NREM3', 'REM', 'Wake', 'Movement',
                      'Artefact']:
            duration[stage] = hypno.count(stage) * self.epoch_length / 60

        slp_onset = sorted(first.values(), key=lambda x: x[1]['start'])[0]
        wake_up = next((len(epochs) - i, j) for i, j in enumerate(
                epochs[::-1]) if j['stage'] in ['NREM1', 'NREM2', 'NREM3',
                                                'REM'])

        total_dark_time = (lights_on - lights_out) / 60
        slp_period_time = (wake_up[1]['start'] - slp_onset[1]['start']) / 60
        slp_onset_lat = (slp_onset[1]['start'] - lights_out) / 60
        waso = (hypno[slp_onset[0]:wake_up[0]].count('Wake') *
                self.epoch_length) / 60
        total_slp_time = slp_period_time - waso
        slp_eff = total_slp_time / total_dark_time

        with open(filename, 'w', newline='') as f:
            lg.info('Writing to' + str(filename))
            csv_file = writer(f)
            csv_file.writerow(['Total dark time',
                               'Sleep onset latency',
                               'Sleep period time',
                               'WASO',
                               'Total sleep time',
                               'Sleep efficiency',
                               'N1 latency',
                               'N2 latency',
                               'N3 latency',
                               'REM latency',
                               'N1 duration',
                               'N2 duration',
                               'N3 duration',
                               'REM duration',
                               'Wake duration',
                               'Movement duration',
                               'Artefact duration',
                               ])
            csv_file.writerow([total_dark_time,
                               slp_onset_lat,
                               slp_period_time,
                               waso,
                               total_slp_time,
                               slp_eff,
                               latency['NREM1'],
                               latency['NREM2'],
                               latency['NREM3'],
                               latency['REM'],
                               duration['NREM1'],
                               duration['NREM2'],
                               duration['NREM3'],
                               duration['REM'],
                               duration['Wake'],
                               duration['Movement'],
                               duration['Artefact'],
                               ])

        return slp_onset_lat, waso, total_slp_time # for testing

    def export_event_data(self, filename, summary, events, cycles=None,
                          fsplit=None):
        """Export event analysis data to CSV, from dialog.

        Parameters
        ----------
        filename : str
            Filename for csv export.
        summary : list of dict
            Parameter name as key with global parameters/avgs as values. If
            fsplit, there are two dicts, low frequency and high frequency
            respectively, combined together in a list.
        events : list of list of dict, optional
            One dictionary per event, each containing  individual event
            parameters. If fsplit, there are two event lists, low frequency
            and high frequency respectively, combined together in a list.
            Otherwise, there is a single list within the master list.
        cycles: int, optional
            Number of cycles.
        fsplit: float, optional
            Frequency at which to split dataset.
        """
        sheets = [filename]

        if cycles:
            sheets = [splitext(filename)[0] + '_cycle' + str(i + 1) + '.csv' \
                      for i in range(len(cycles))]

        if fsplit:
            all_sheets = []

            for fn in sheets:
                all_sheets.extend([splitext(fn)[0] + '_slow.csv',
                                   splitext(fn)[0] + '_fast.csv'])

            sheets = all_sheets

        ordered_params = ['dur', 'maxamp', 'ptp', 'peakf', 'power', 'rms',
                          'count', 'density']
        headings = ['Duration (s)',
                    'Maximum amplitude (uV)',
                    'Peak-to-peak amplitude (uV)',
                    'Peak frequency (Hz)',
                    'Average power (uV^2)',
                    'RMS (uV)',
                    'Count',
                    'Density']
        idx_params = in1d(ordered_params, list(summary[0].keys()))
        sel_params_in_order = list(compress(ordered_params, idx_params))
        per_evt_params = list(compress(ordered_params[:-2], idx_params))

        lg.info('sheets: ' + str(len(sheets)) + ' summ: ' + str(len(summary)) + 'events: ' + str(len(events)))
        if events is not None:
            lg.info('number of events ' + str(len(events[0])))

        for fn, summ, evs in zip(sheets, summary, events):
            first_row = list(compress(headings, idx_params))
            second_row = [summ[key][0] for key in sel_params_in_order]

            if evs:
                first_row[:0] = ['Index', 'Start (clock)', 'Start (record)',
                                'End (record)', 'Channel', 'Stage']
                second_row[:0] = ['Mean', '', '', '', '', '']
                third_row = ['SD', '', '', '', '', ''] + \
                        [summ[key][1] for key in per_evt_params]

            with open(fn, 'w', newline='') as f:
                lg.info('Writing to' + fn)
                csv_file = writer(f)
                csv_file.writerow(first_row)
                csv_file.writerow(second_row)

                if evs:
                    csv_file.writerow(third_row)

                    for i, ev in enumerate(evs):
                        ev_time = (self.start_time +
                                      timedelta(seconds=ev['start']))
                        if isinstance(ev['chan'], (tuple, list)):
                            ev['chan'] = ', '.join(ev['chan'])
                        info_row = [i+1,
                                    ev_time.strftime('%H:%M:%S'),
                                    ev['start'],
                                    ev['end'],
                                    ev['chan'],
                                    ev['stage']]
                        data_row = [ev[key] for key in per_evt_params]
                        csv_file.writerow(info_row + data_row)


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
