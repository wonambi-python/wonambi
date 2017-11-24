from datetime import datetime, timezone
from logging import getLogger, NOTSET, WARNING, disable
from os import SEEK_SET, SEEK_CUR, SEEK_END
from os.path import splitext
from struct import unpack

from numpy import (asarray, empty, expand_dims, fromfile, iinfo, NaN, ones,
                   reshape, where)

lg = getLogger(__name__)

BLACKROCK_FORMAT = 'int16'  # by definition
blackrock_iinfo = iinfo(BLACKROCK_FORMAT)
N_BYTES = int(blackrock_iinfo.bits / 8)


class BlackRock:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = filename
        self.markers = []

        self.BOData = None
        self.sess_begin = None
        self.sess_end = None
        self.factor = None

    def return_hdr(self):
        """Return the header for further use.

        Parameters
        ----------
        trigger_bits : int, optional
            8 or 16, read the triggers as one or two bytes
        trigger_zero : bool, optional
            read the trigger zero or not

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

        Notes
        -----
        The implementation needs to be updated for NEURALSG

        """
        with open(self.filename, 'rb') as f:
            file_header = f.read(8)

        if file_header == b'NEURALEV':
            orig = _read_neuralev(self.filename)

            s_freq = orig['SampleRes']
            n_samples = orig['DataDuration']
            chan_name = []  # TODO: digital channels here instead of notes

        elif file_header == b'NEURALCD':
            orig = _read_neuralcd(self.filename)

            s_freq = orig['SamplingFreq']
            n_samples = sum(orig['DataPoints']) + sum(orig['Timestamps'])
            chan_name = [x['Label'] for x in orig['ElectrodesInfo']]

            # INFO to read the data
            self.BOData = orig['BOData']
            self.sess_begin, self.sess_end = _calc_sess_intervals(orig)
            self.factor = _convert_factor(orig['ElectrodesInfo'])

            nev_file = splitext(self.filename)[0] + '.nev'
            try:
                disable(WARNING)
                nev_orig = _read_neuralev(nev_file)
                disable(NOTSET)
            except FileNotFoundError:
                pass

            else:
                nev_orig.update(orig)  # precedence to orig
                orig = nev_orig

        elif file_header == b'NEURALSG':
            orig = _read_neuralsg(self.filename)
            # raise NotImplementedError('This implementation needs to be updated')

            s_freq = orig['SamplingFreq']
            n_samples = orig['DataPoints']

            self.n_samples = n_samples
            self.factor = 0.25 * ones(len(orig['ChannelID']))

            # make up names
            chan_name = ['chan{0:04d}'.format(x) for x in orig['ChannelID']]

        subj_id = str()
        start_time = orig['DateTime']

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
        ext = splitext(self.filename)[1]
        if ext == '.nev':
            raise TypeError('NEV contains only header info, not data')

        data = _read_nsx(self.filename, self.BOData, self.sess_begin,
                         self.sess_end, self.factor, begsam, endsam)

        return data[chan, :]

    def return_markers(self, trigger_bits=8, trigger_zero=True):
        """We always read triggers as 16bit, but we convert them to 8 here
        if requested.

        """
        nev_file = splitext(self.filename)[0] + '.nev'
        markers = _read_neuralev(nev_file, read_markers=True)

        if trigger_bits == 8:
            to8 = lambda x: str(int(x) - (256 ** 2 - 256))
            for m in markers:
                m['name'] = to8(m['name'])

        if trigger_zero:
            no_zero = (i for i, m in enumerate(markers) if m['name'] != '0')

            markers_no_zero = []
            for i in no_zero:
                if (i + 1) < len(markers) and markers[i + 1]['name'] == '0':
                    markers[i]['end'] = markers[i + 1]['start']
                markers_no_zero.append(markers[i])

        return markers_no_zero


def _read_nsx(filename, BOData, sess_begin, sess_end, factor, begsam, endsam):
    """

    Notes
    -----
    Tested on NEURALCD

    It returns NaN if you select an interval outside of the data
    """
    n_chan = factor.shape[0]

    dat = empty((n_chan, endsam - begsam))
    dat.fill(NaN)

    sess_to_read = where((begsam < sess_end) & (endsam > sess_begin))[0]

    with open(filename, 'rb') as f:

        for sess in sess_to_read:
            begsam_sess = begsam - sess_begin[sess]
            endsam_sess = endsam - sess_begin[sess]

            begshift = 0

            if begsam_sess < 0:
                begsam_sess = 0
                begshift = sess_begin[sess] - begsam

            if endsam_sess > (sess_end[sess] - sess_begin[sess]):
                endsam_sess = (sess_end[sess] - sess_begin[sess])

            endshift = begshift + endsam_sess - begsam_sess

            f.seek(BOData[sess], SEEK_SET)
            f.seek(n_chan * N_BYTES * begsam_sess, SEEK_CUR)

            n_sam = endsam_sess - begsam_sess
            dat_in_file = fromfile(f, BLACKROCK_FORMAT, n_chan * n_sam)

            dat[:, begshift:endshift] = reshape(dat_in_file, (n_chan, n_sam),
                                                order='F')

    return expand_dims(factor, 1) * dat


def _read_neuralsg(filename):
    """


    """
    hdr = {}
    with open(filename, 'rb') as f:

        hdr['FileTypeID'] = f.read(8).decode('utf-8')
        hdr['FileSpec'] = '2.1'
        hdr['SamplingLabel'] = _str(f.read(16).decode('utf-8'))
        hdr['TimeRes'] = 30000
        hdr['SamplingFreq'] = int(hdr['TimeRes'] / unpack('<I', f.read(4))[0])
        n_chan = unpack('<I', f.read(4))[0]
        hdr['ChannelCount'] = n_chan
        hdr['ChannelID'] = unpack('<' + 'I' * n_chan, f.read(4 * n_chan))

        BOData = f.tell()
        f.seek(0, SEEK_END)
        EOData = f.tell()

    # we read the time information from the corresponding NEV file
    nev_filename = splitext(filename)[0] + '.nev'
    with open(nev_filename, 'rb') as f:
        f.seek(28)
        time = unpack('<' + 'H' * 8, f.read(16))

    hdr['DateTimeRaw'] = time
    lg.warning('DateTime is in local time')
    hdr['DateTime'] = datetime(time[0], time[1], time[3],
                               time[4], time[5], time[6], time[7] * 1000)

    hdr['DataPoints'] = int((EOData - BOData) / (n_chan * N_BYTES))
    hdr['BOData'] = BOData

    return hdr


def _read_neuralcd(filename):
    """

    Notes
    -----
    The time stamps are stored in UTC in the NSx files. However, time stamps
    in the NEV files are stored as local time up to Central 6.03 included and
    stored as UTC after Central 6.05. It's impossible to know the version of
    Central from the header.
    """
    hdr = {}
    with open(filename, 'rb') as f:
        hdr['FileTypeID'] = f.read(8).decode('utf-8')

        BasicHdr = f.read(306)
        filespec = unpack('bb', BasicHdr[0:2])
        hdr['FileSpec'] = str(filespec[0]) + '.' + str(filespec[1])
        hdr['HeaderBytes'] = unpack('<I', BasicHdr[2:6])[0]
        hdr['SamplingLabel'] = _str(BasicHdr[6:22].decode('utf-8'))
        hdr['Comment'] = _str(BasicHdr[22:278].decode('utf-8', 'ignore'))
        hdr['TimeRes'] = unpack('<I', BasicHdr[282:286])[0]
        hdr['SamplingFreq'] = int(hdr['TimeRes'] /
                                  unpack('<i', BasicHdr[278:282])[0])
        time = unpack('<' + 'H' * 8, BasicHdr[286:302])
        hdr['DateTimeRaw'] = time
        lg.warning('DateTime is in UTC time')
        hdr['DateTime'] = datetime(time[0], time[1], time[3], time[4], time[5],
                                   time[6], time[7] * 1000,
                                   tzinfo=timezone.utc)
        hdr['ChannelCount'] = unpack('<I', BasicHdr[302:306])[0]

        ExtHdrLength = 66
        readSize = hdr['ChannelCount'] * ExtHdrLength
        ExtHdr = f.read(readSize)

        ElectrodesInfo = []
        for idx in range(hdr['ChannelCount']):
            i1 = idx * ExtHdrLength
            elec = {}
            i0, i1 = i1, i1 + 2
            elec['Type'] = ExtHdr[i0:i1].decode('utf-8')
            assert elec['Type'] == 'CC'
            i0, i1 = i1, i1 + 2
            elec['ElectrodeID'] = unpack('<H', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 16
            elec['Label'] = _str(ExtHdr[i0:i1].decode('utf-8'))
            i0, i1 = i1, i1 + 1
            elec['ConnectorBank'] = chr(unpack('<B', ExtHdr[i0:i1])[0] +
                                        ord('A') - 1)
            i0, i1 = i1, i1 + 1
            elec['ConnectorPin'] = unpack('<B', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['MinDigiValue'] = unpack('<h', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['MaxDigiValue'] = unpack('<h', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['MinAnalogValue'] = unpack('<h', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['MaxAnalogValue'] = unpack('<h', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 16
            elec['AnalogUnits'] = _str(ExtHdr[i0:i1].decode('utf-8'))
            i0, i1 = i1, i1 + 4
            elec['HighFreqCorner'] = unpack('<I', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            elec['HighFreqOrder'] = unpack('<I', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['HighFilterType'] = unpack('<H', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            elec['LowFreqCorner'] = unpack('<I', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            elec['LowFreqOrder'] = unpack('<I', ExtHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 2
            elec['LowFilterType'] = unpack('<H', ExtHdr[i0:i1])[0]
            ElectrodesInfo.append(elec)

        hdr['ElectrodesInfo'] = ElectrodesInfo
        hdr['ChannelID'] = [x['ElectrodeID'] for x in ElectrodesInfo]

        EOexH = f.tell()
        f.seek(0, SEEK_END)
        EOF = f.tell()
        f.seek(EOexH, SEEK_SET)
        n_chan = hdr['ChannelCount']

        if f.tell() >= EOF:
            raise EOFError('File {0} does not seem to contain data '
                           '(size {1} B)'.format(filename, EOF))

        BOData = []
        EOData = []
        Timestamps = []
        DataPoints = []

        while f.tell() < EOF and f.read(1) == b'\x01':

            Timestamps.append(unpack('<I', f.read(4))[0])

            DataPoint = unpack('<I', f.read(4))[0]
            DataPoints.append(DataPoint)

            BOData.append(f.tell())
            f.seek(N_BYTES * DataPoint * n_chan, SEEK_CUR)
            EOData.append(f.tell())

        # the last datapoint does not get updated, so it remains 0
        if DataPoints[-1] == 0:

            # we need to update EOData, because it depends on DataPoint
            EOData[-1] = EOF

            # we back compute the last DataPoint
            DataPoints[-1] = int((EOData[-1] - BOData[-1]) / N_BYTES / n_chan)

        hdr['BOData'] = BOData
        hdr['EOData'] = EOData
        hdr['Timestamps'] = Timestamps  # sampled at 'TimeRes' Hz, ie 30000
        hdr['DataPoints'] = DataPoints

    return hdr


def _read_neuralev(filename, read_markers=False, trigger_bits=16,
                   trigger_zero=True):
    """Read some information from NEV

    Parameters
    ----------
    filename : str
        path to NEV file
    read_markers : bool
        whether to read markers or not (it can get really large)
    trigger_bits : int, optional
        8 or 16, read the triggers as one or two bytes
    trigger_zero : bool, optional
        read the trigger zero or not

    Returns
    -------
    MetaTags : list of dict
        which corresponds to MetaTags of openNEV
    Markers : list of dict
        markers in NEV file

    Notes
    -----
    The conversion to DateTime in openNEV.m is not correct. They add a value of
    2 to the day. Instead, they should add it to the index of the weekday

    It returns triggers as strings (format of EDFBrowser), but it does not read
    the othe types of events (waveforms, videos, etc).

    The time stamps are stored in UTC in the NSx files. However, time stamps
    in the NEV files are stored as local time up to Central 6.03 included and
    stored as UTC after Central 6.05. It's impossible to know the version of
    Central from the header.
    """
    hdr = {}
    with open(filename, 'rb') as f:

        BasicHdr = f.read(336)

        i1 = 8
        hdr['FileTypeID'] = BasicHdr[:i1].decode('utf-8')
        assert hdr['FileTypeID'] == 'NEURALEV'
        i0, i1 = i1, i1 + 2
        filespec = unpack('bb', BasicHdr[i0:i1])
        hdr['FileSpec'] = str(filespec[0]) + '.' + str(filespec[1])
        i0, i1 = i1, i1 + 2
        hdr['Flags'] = unpack('<H', BasicHdr[i0:i1])[0]
        i0, i1 = i1, i1 + 4
        hdr['HeaderOffset'] = unpack('<I', BasicHdr[i0:i1])[0]
        i0, i1 = i1, i1 + 4
        hdr['PacketBytes'] = unpack('<I', BasicHdr[i0:i1])[0]
        i0, i1 = i1, i1 + 4
        hdr['TimeRes'] = unpack('<I', BasicHdr[i0:i1])[0]
        i0, i1 = i1, i1 + 4
        hdr['SampleRes'] = unpack('<I', BasicHdr[i0:i1])[0]
        i0, i1 = i1, i1 + 16
        time = unpack('<' + 'H' * 8, BasicHdr[i0:i1])
        hdr['DateTimeRaw'] = time
        lg.warning('DateTime is in local time with Central version <= 6.03'
                   ' and in UTC with Central version > 6.05')
        hdr['DateTime'] = datetime(time[0], time[1], time[3],
                                   time[4], time[5], time[6], time[7] * 1000)
        i0, i1 = i1, i1 + 32
        # hdr['Application'] = _str(BasicHdr[i0:i1].decode('utf-8'))
        i0, i1 = i1, i1 + 256
        hdr['Comment'] = _str(BasicHdr[i0:i1].decode('utf-8',
                                                     errors='replace'))
        i0, i1 = i1, i1 + 4
        countExtHeader = unpack('<I', BasicHdr[i0:i1])[0]

        # you can read subject name from sif

        # Check data duration
        f.seek(-hdr['PacketBytes'], SEEK_END)
        hdr['DataDuration'] = unpack('<I', f.read(4))[0]
        hdr['DataDurationSec'] = hdr['DataDuration'] / hdr['SampleRes']

        # Read the Extended Header
        f.seek(336)
        ElectrodesInfo = []
        IOLabels = []

        for i in range(countExtHeader):

            ExtendedHeader = f.read(32)
            i1 = 8
            PacketID = ExtendedHeader[:i1].decode('utf-8')

            if PacketID == 'NEUEVWAV':
                elec = {}
                i0, i1 = i1, i1 + 2
                elec['ElectrodeID'] = unpack('<H', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 1
                elec['ConnectorBank'] = chr(ExtendedHeader[i0] + 64)
                i0, i1 = i1, i1 + 1
                elec['ConnectorPin'] = ExtendedHeader[i0]
                i0, i1 = i1, i1 + 2
                df = unpack('<h', ExtendedHeader[i0:i1])[0]
                # This is a workaround for the DigitalFactor overflow
                if df == 21516:
                    elec['DigitalFactor'] = 152592.547
                else:
                    elec['DigitalFactor'] = df

                i0, i1 = i1, i1 + 2
                elec['EnergyThreshold'] = unpack('<H', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['HighThreshold'] = unpack('<h', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['LowThreshold'] = unpack('<h', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 1
                elec['Units'] = ExtendedHeader[i0]
                i0, i1 = i1, i1 + 1
                elec['WaveformBytes'] = ExtendedHeader[i0]
                ElectrodesInfo.append(elec)

            elif PacketID == 'NEUEVLBL':
                i0, i1 = i1, i1 + 2
                ElectrodeID = unpack('<H', ExtendedHeader[i0:i1])[0] - 1
                s = _str(ExtendedHeader[i1:].decode('utf-8'))
                ElectrodesInfo[ElectrodeID]['ElectrodeLabel'] = s

            elif PacketID == 'NEUEVFLT':
                elec = {}
                i0, i1 = i1, i1 + 2
                ElectrodeID = unpack('<H', ExtendedHeader[i0:i1])[0] - 1
                i0, i1 = i1, i1 + 4
                elec['HighFreqCorner'] = unpack('<I', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['HighFreqOrder'] = unpack('<I', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['HighFilterType'] = unpack('<H', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['LowFreqCorner'] = unpack('<I', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['LowFreqOrder'] = unpack('<I', ExtendedHeader[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['LowFilterType'] = unpack('<H', ExtendedHeader[i0:i1])[0]
                ElectrodesInfo[ElectrodeID].update(elec)

            elif PacketID == 'DIGLABEL':
                # TODO: the order is not taken into account and probably wrong!
                iolabel = {}

                iolabel['mode'] = ExtendedHeader[24] + 1
                s = _str(ExtendedHeader[8:25].decode('utf-8'))
                iolabel['label'] = s
                IOLabels.append(iolabel)

            else:
                raise NotImplementedError(PacketID + ' not implemented yet')

        hdr['ChannelID'] = [x['ElectrodeID'] for x in ElectrodesInfo]

        fExtendedHeader = f.tell()
        fData = f.seek(0, SEEK_END)
        countDataPacket = int((fData - fExtendedHeader) / hdr['PacketBytes'])

        markers = []
        if read_markers and countDataPacket:

            f.seek(fExtendedHeader)
            x = f.read(countDataPacket * hdr['PacketBytes'])

            DigiValues = []
            for j in range(countDataPacket):
                i = j * hdr['PacketBytes']

                if trigger_bits == 16:
                    tempDigiVals = unpack('<H', x[8 + i:10 + i])[0]
                else:
                    tempDigiVals = unpack('<H', x[8 + i:9 + i] + b'\x00')[0]

                val = {'timestamp': unpack('<I', x[0 + i:4 + i])[0],
                       'packetID': unpack('<H', x[4 + i:6 + i])[0],
                       'tempClassOrReason': unpack('<B', x[6 + i:7 + i])[0],
                       'tempDigiVals': tempDigiVals}

                if tempDigiVals != 0 or False:
                    DigiValues.append(val)

            digserPacketID = 0
            not_serialdigital = [x for x in DigiValues
                                 if not x['packetID'] == digserPacketID]

            if not_serialdigital:
                lg.debug('Code not implemented to read PacketID ' +
                         str(not_serialdigital[0]['packetID']))

            # convert to markers
            for val in DigiValues:
                m = {'name': str(val['tempDigiVals']),
                     'start': val['timestamp'] / hdr['SampleRes'],
                     'end': val['timestamp'] / hdr['SampleRes'],
                     'chan': [''],
                     }
                markers.append(m)

    if read_markers:
        return markers
    else:
        return hdr


def _str(t_in):
    t_out = []
    for t in t_in:
        if t == '\x00':
            break
        t_out.append(t)
    return ''.join(t_out)


def _convert_factor(ElectrodesInfo):

    factor = []
    for elec in ElectrodesInfo:

        # have to be equal, so it's simple to calculate conversion factor
        assert elec['MaxDigiValue'] == -elec['MinDigiValue']
        assert elec['MaxAnalogValue'] == -elec['MinAnalogValue']

        factor.append((elec['MaxAnalogValue'] - elec['MinAnalogValue']) /
                      (elec['MaxDigiValue'] - elec['MinDigiValue']))

    return asarray(factor)


def _calc_sess_intervals(hdr):

    sess_begin = []
    sess_end = []
    n_sess = len(hdr['Timestamps'])

    # timestamps are always at 30 kHz, so we need to convert
    sampling_inverval = hdr['TimeRes'] / hdr['SamplingFreq']

    for i in range(n_sess):

        sess_smp_begin = (sum(hdr['DataPoints'][:i]) +
                          sum(hdr['Timestamps'][:i + 1]) / sampling_inverval)
        sess_begin.append(sess_smp_begin)

        sess_smp_end = (sum(hdr['DataPoints'][:i + 1]) +
                        sum(hdr['Timestamps'][:i + 1]) / sampling_inverval)
        sess_end.append(sess_smp_end)

    sess_begin = asarray(sess_begin, dtype=int)
    sess_end = asarray(sess_end, dtype=int)

    return sess_begin, sess_end
