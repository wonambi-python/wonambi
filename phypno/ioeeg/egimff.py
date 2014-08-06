from datetime import datetime
from glob import glob
from os import SEEK_CUR
from os.path import join
from struct import unpack
from xml.etree.ElementTree import parse

from numpy import append, cumsum, diff, empty, asarray, NaN, reshape, where


class EgiMff:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = filename
        self._signal = []
        self._block_hdr = []
        self._i_data = []
        self._n_samples = []

    def return_hdr(self):
        """Return the header for further use.

        Returns
        -------
        subj_id : str
            subject identification code
        start_time : datetime
            start time of the dataset
        s_freq : float
            sampling frequency
        chan_name : list of str
            list of all the channels
        n_samples : int
            number of samples in the dataset
        orig : dict
            additional information taken directly from the header

        """
        xml_files = ['info', 'history', 'workflow', 'subject', 'coordinates',
                     'sensorLayout', 'epochs', ]

        orig = {}
        for xml_file in xml_files:
            try:
                orig[xml_file] = parse_xml(join(self.filename,
                                                xml_file + '.xml'))
            except FileNotFoundError:
                orig[xml_file] = None

        signals = glob(join(self.filename, 'signal*.bin'))

        for signal in signals:
            block_hdr, i_data = read_all_block_hdr(join(self.filename, signal))
            self._signal.append(signal)
            self._block_hdr.append(block_hdr)
            self._i_data.append(i_data)
            n_samples = asarray([x['n_samples'][0] for x in block_hdr], 'q')
            self._n_samples.append(n_samples)

        subj_id = orig['subject']['fields']['field']['name']
        shorttime = lambda x: x[:26] + x[29:32] + x[33:]
        start_time = datetime.strptime(shorttime(orig['info']['recordTime']),
                                       '%Y-%m-%dT%H:%M:%S.%f%z')

        # it only works if they have all the same sampling frequency
        s_freq = [x[0]['freq'][0] for x in self._block_hdr]
        assert all([x == s_freq[0] for x in s_freq])
        SIGNAL = 0
        s_freq = block_hdr[SIGNAL]['freq'][0]

        sensors = orig['sensorLayout']['sensors']['sensor']
        chan_name = []
        for one_sensor in sensors:
            if one_sensor['name'] is not None:
                chan_name.append(one_sensor['name'])
            else:
                chan_name.append(one_sensor['number'])

        n_samples = block_hdr[SIGNAL]['opt_hdr']['n_smp']
        orig = orig

        return subj_id, start_time, s_freq, chan_name, n_samples, orig

    def return_dat(self, chan, begsam, endsam):
        """Return the data as 2D numpy.ndarray.

        Parameters
        ----------
        chan : int or list
            index (indices) of the channels to read
        begsam : int
            index of the first sample
        endsam : int
            index of the last sample

        Returns
        -------
        numpy.ndarray
            A 2d matrix, with dimension chan X samples

        """
        assert begsam < endsam

        data = empty((len(chan), endsam - begsam))
        data.fill(NaN)

        begsam = float(begsam)
        endsam = float(endsam)

        SIGNAL = 0
        x = append(0, self._n_samples[SIGNAL])
        x1 = cumsum(x)

        begrec = where(begsam < x1)[0][0] - 1
        endrec = where(endsam < x1)[0][0] - 1

        i0 = 0
        for rec in range(begrec, endrec + 1):
            rec_dat = _read_block(self._signal[SIGNAL],
                                  self._block_hdr[SIGNAL][rec],
                                  self._i_data[SIGNAL][rec])

            if rec == begrec:
                begpos_rec = begsam - x1[rec]
            else:
                begpos_rec = 0

            if rec == endrec:
                endpos_rec = endsam - x1[rec]
            else:
                endpos_rec = x[rec]

            i1 = i0 + endpos_rec - begpos_rec
            data[:, i0:i1] = rec_dat[chan, begpos_rec:endpos_rec]
            i0 = i1

        return data


def _read_block(filename, block_hdr, i):

    n_bytes = (block_hdr['depth'] / 8).astype('B')

    data_type = []
    for b, n_smp in zip(n_bytes, block_hdr['n_samples']):
        if b == 2:
            data_type.append('h' * n_smp)
        if b == 4:
            data_type.append('f' * n_smp)
        if b == 8:
            data_type.append('d' * n_smp)

    with open(filename, 'rb') as f:
        f.seek(i)

        v = unpack('<' + ''.join(data_type),
                   f.read(sum(n_bytes * block_hdr['n_samples'])))

    return reshape(v, (block_hdr['n_signals'], block_hdr['n_samples'][0]))


def read_block_hdr(f):

    version = unpack('<I', f.read(4))[0]
    hdr_size = unpack('<I', f.read(4))[0]
    data_size = unpack('<I', f.read(4))[0]
    n_signals = unpack('<I', f.read(4))[0]

    offset = asarray(unpack('<' + 'I' * n_signals, f.read(4 * n_signals)), 'I')

    depth = empty(n_signals, 'B')
    freq = empty(n_signals, 'I')
    for j in range(n_signals):
        depth[j] = unpack('<B', f.read(1))[0]
        freq[j] = unpack('<I', f.read(3) + b'\x00')[0]

    n_samples = diff(offset)
    n_samples = append(n_samples, data_size - offset[-1])
    n_samples = (n_samples / (depth / 8)).astype('I')

    opt_hdr_size = unpack('<I', f.read(4))[0]
    opt_hdr_type = unpack('<I', f.read(4))[0]
    if opt_hdr_type == 1:
        n_blocks = unpack('<Q', f.read(8))[0]
        n_smp = unpack('<Q', f.read(8))[0]
        n_signals_opt = unpack('<I', f.read(4))[0]
    else:
        n_blocks = None
        n_smp = None
        n_signals_opt = None

    opt_hdr = {'n_blocks': n_blocks,
               'n_smp': n_smp,
               'n_signals_opt': n_signals_opt}

    hdr = {'version': version,
           'hdr_size': hdr_size,
           'data_size': data_size,
           'n_signals': n_signals,
           'offset': offset,
           'depth': depth,
           'freq': freq,
           'n_samples': n_samples,
           'opt_hdr_size': opt_hdr_size,
           'opt_hdr': opt_hdr,
           }

    return hdr


def read_all_block_hdr(filename):

    with open(filename, 'rb') as f:

        block_hdr = []
        i_data = []

        while True:
            version_bytes = f.read(4)
            if not version_bytes:
                break
            version = unpack('<I', version_bytes)[0]

            if version:
                f.seek(-4, SEEK_CUR)  # re-read version
                block_hdr.append(read_block_hdr(f))

            else:
                block_hdr.append(block_hdr[-1])

            i_data.append(f.tell())
            f.seek(block_hdr[-1]['data_size'], SEEK_CUR)

        i_data = asarray(i_data, 'q')

    return block_hdr, i_data


def parse_xml(xml_file):
    xml = parse(xml_file)
    root = xml.getroot()
    return xml2dict(root)


def xml2list(one_list):
    output = []
    for element in one_list:
        if element:
            if len(element) == 1 or element[0].tag != element[1].tag:
                output.append(xml2dict(element))
            elif element[0].tag == element[1].tag:
                output.append(xml2list(element))

        elif element.text:
            text = element.text.strip()
            if text:
                output.append(text)

    return output


def xml2dict(root):
    """Use functions instead of Class and remove namespace based on:
    http://stackoverflow.com/questions/2148119
    """
    # remove namespace
    ns = lambda s: '}'.join(s.split('}')[1:])

    output = {}
    if root.items():
        output.update(dict(root.items()))

    for element in root:
        if element:
            if len(element) == 1 or element[0].tag != element[1].tag:
                one_dict = xml2dict(element)
            else:
                one_dict = {ns(element[0].tag): xml2list(element)}

            if element.items():
                one_dict.update(dict(element.items()))
            output.update({ns(element.tag): one_dict})

        elif element.items():
            output.update({ns(element.tag): dict(element.items())})

        else:
            output.update({ns(element.tag): element.text})

    return output
