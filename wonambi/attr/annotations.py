"""Module to keep track of the user-made annotations and sleep scoring.
"""
from logging import getLogger
from csv import writer
from datetime import datetime, timedelta
from math import ceil
from re import search, sub
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString

lg = getLogger(__name__)
VERSION = '5'


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
    with open(xml_file, 'w') as f:
        f.write(xml.toxml())


class Annotations():
    """Class to return nicely formatted information from xml.

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
        """
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
                    time_cond = time[0] == event_start and time[1] == event_end

                if chan is None:
                    chan_cond = True
                else:
                    chan_cond = event_chan == chan

                if time_cond and chan_cond:
                    e_type.remove(e)

        self.save()

    def get_events(self, name=None, time=None, chan=None):
        """Get list of events in the file.

        Parameters
        ----------
        name : str, optional
            name of the event of interest
        time : tuple of two float, optional
            start and end time of the period of interest
        chan : tuple of str, optional
            list of channels of interests

        Returns
        -------
        list of dict
            where each dict has 'name' (name of the event), 'start' (start
            time), 'end' (end time), 'chan' (channels of interest, can be
            empty)

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

        ev = []
        for e_type in events.iterfind(pattern):

            event_name = e_type.get('type')

            for e in e_type:

                event_start = float(e.find('event_start').text)
                event_end = float(e.find('event_end').text)
                event_chan = e.find('event_chan').text
                if event_chan is None:  # xml doesn't store empty string
                    event_chan = ''

                if time is None:
                    time_cond = True
                else:
                    time_cond = time[0] <= event_end and time[1] >= event_start

                if chan is None:
                    chan_cond = True
                else:
                    chan_cond = event_chan == chan

                if time_cond and chan_cond:
                    one_ev = {'name': event_name,
                              'start': event_start,
                              'end': event_end,
                              'chan': event_chan.split(', '),  # always a list
                              }
                    ev.append(one_ev)

        return ev

    def create_epochs(self, epoch_length=30):
        last_sec = ceil((self.last_second - self.first_second) /
                        epoch_length) * epoch_length

        stages = self.rater.find('stages')
        for epoch_beg in range(self.first_second, last_sec, epoch_length):
            epoch = SubElement(stages, 'epoch')

            start_time = SubElement(epoch, 'epoch_start')
            start_time.text = str(epoch_beg)

            end_time = SubElement(epoch, 'epoch_end')
            end_time.text = str(epoch_beg + epoch_length)

            stage = SubElement(epoch, 'stage')
            stage.text = 'Unknown'

    @property
    def epochs(self):
        """Get epochs as generator

        Returns
        -------
        list of dict
            each epoch is defined by start_time and end_time (in s in reference
            to the start of the recordings) and a string of the sleep stage.
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
                     }
            yield epoch

    def get_stage_for_epoch(self, epoch_start):
        """Return stage for one specific epoch.

        Parameters
        ----------
        id_epoch : str
            index of the epoch

        Returns
        -------
        stage : str
            description of the stage.

        """

        for epoch in self.epochs:
            if epoch['start'] == epoch_start:
                return epoch['stage']

    def time_in_stage(self, stage):
        """Return time (in seconds) in the selected stage.

        Parameters
        ----------
        stage : str
            one of the sleep stages

        Returns
        -------
        int
            time spent in one stage, in seconds.

        """
        return sum(x['end'] - x['start'] for x in self.epochs
                   if x['stage'] == stage)

    def set_stage_for_epoch(self, epoch_start, stage):
        """Change the stage for one specific epoch.

        Parameters
        ----------
        id_epoch : str
            index of the epoch
        stage : str
            description of the stage.

        Raises
        ------
        KeyError
            When the id_epoch is not in the list of epochs.
        IndexError
            When there is no rater / epochs at all
        """
        if self.rater is None:
            raise IndexError('You need to have at least one rater')

        for one_epoch in self.rater.iterfind('stages/epoch'):
            if int(one_epoch.find('epoch_start').text) == epoch_start:
                one_epoch.find('stage').text = stage
                self.save()
                return

        raise KeyError('epoch starting at ' + str(epoch_start) + ' not found')

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
