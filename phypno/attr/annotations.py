"""Module to keep track of the score.

There is nothing in this module that can create a xml score file. That's
because the only way to create a score is by scoring the data, visually. Once
you have the score file, you can work with it programmatically with this
module.

"""
from logging import getLogger
lg = getLogger(__name__)

from datetime import datetime
from math import ceil
from os.path import basename
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString


def create_empty_annotations(xml_file, dataset):
    """Create an empty annotation file."""
    root = Element('annotations')
    root.set('version', '3')

    info = SubElement(root, 'dataset')
    x = SubElement(info, 'filename')
    x.text = basename(dataset.filename)
    x = SubElement(info, 'path')  # not to be relied on
    x.text = dataset.filename
    x = SubElement(info, 'start_time')
    x.text = dataset.header['start_time'].isoformat()

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
        lg.info('Loading ' + self.xml_file)
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
        xml_dataset = self.root.find('dataset')

        start_time = datetime.strptime(xml_dataset.find('start_time').text,
                                       '%Y-%m-%dT%H:%M:%S')
        output = {'start_time': start_time,
                  'first_second': int(xml_dataset.find('first_second').text),
                  'last_second': int(xml_dataset.find('last_second').text)
                  }

        return output

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

    def add_rater(self, rater_name):
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
        SubElement(self.rater, 'markers')
        SubElement(self.rater, 'events')
        SubElement(self.rater, 'stages')
        self.create_epochs()

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

    def add_marker(self, name, time):
        markers = self.rater.find('markers')
        new_marker = SubElement(markers, 'marker')
        marker_name = SubElement(new_marker, 'name')
        marker_name.text = name
        marker_time = SubElement(new_marker, 'time')
        marker_time.text = str(time)

        self.save()

    def remove_marker(self, name):
        # how to remove? Maybe unique ID
        pass

    def get_markers(self, win_interval=None):
        # get markers inside window
        markers = self.rater.find('markers')

        mrks = []
        for m in markers:

            time = float(m.find('time').text)
            if win_interval is None:
                win_cond = True
            else:
                win_cond = win_interval[0] <= time < win_interval[1]

            if win_cond:
                one_mrk = {'name': m.find('name').text,
                           'time': time}
                mrks.append(one_mrk)

        return mrks

    def add_event(self, name, time):
        events = self.rater.find('events')
        new_event = SubElement(events, 'event')
        event_name = SubElement(new_event, 'name')
        event_name.text = name
        event_start = SubElement(new_event, 'event_start')
        event_start.text = str(time[0])
        event_end = SubElement(new_event, 'event_end')
        event_end.text = str(time[1])

        self.save()

    def remove_event(self, win_interval=None, name=None):
        # remove events based on window interval and/or name
        pass

    def get_events(self, win_interval=None, name=None):
        # get events inside window
        events = self.rater.find('events')
        ev = []
        for e in events:

            event_name = e.find('name').text
            if name is None:
                name_cond = True
            else:
                name_cond = event_name == name

            event_start = float(e.find('event_start').text)
            event_end = float(e.find('event_end').text)
            if win_interval is None:
                win_cond = True
            else:
                win_cond = (win_interval[0] <= event_end and
                            win_interval[1] >= event_start)

            if win_cond and name_cond:

                one_ev = {'name': event_name,
                          'start': event_start,
                          'end': event_end,
                          }
                ev.append(one_ev)
        return ev

    def create_epochs(self, epoch_length=30):
        first_sec = int(self.root.find('dataset/first_second').text)
        last_sec = int(self.root.find('dataset/last_second').text)
        last_sec = ceil((last_sec - first_sec) / epoch_length) * epoch_length

        stages = self.rater.find('stages')
        for epoch_beg in range(first_sec, last_sec, epoch_length):
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

        """
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

        """
        for one_epoch in self.rater.iterfind('stages/epoch'):
            if int(one_epoch.find('epoch_start').text) == epoch_start:
                one_epoch.find('stage').text = stage
                self.save()
                return

        raise KeyError('epoch starting at ' + str(epoch_start) + ' not found')
