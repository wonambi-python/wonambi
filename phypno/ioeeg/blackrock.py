from datetime import datetime, timedelta
from os import SEEK_SET, SEEK_CUR, SEEK_END
from os.path import splitext
from struct import unpack

from numpy import fromfile, reshape, asarray, expand_dims, ones

from ..utils.timezone import Eastern, utc


class BlackRock:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    """
    def __init__(self, filename):
        self.filename = filename

    def return_hdr(self, trigger_bits=8, trigger_zero=False):
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
        BOData and factor

        What is the difference between NEURALCD and NEURALSG?

        """
        with open(self.filename, 'rb') as f:
            file_header = f.read(8)

        if file_header == b'NEURALEV':
            orig = _read_neuralev(self.filename, trigger_bits=trigger_bits,
                                  trigger_zero=trigger_zero)[0]

            s_freq = orig['SampleRes']
            n_samples = orig['DataDuration']
            chan_name = []  # TODO: digital channels here instead of notes

        elif file_header == b'NEURALCD':
            orig = _read_neuralcd(self.filename)

            s_freq = orig['SamplingFreq']
            n_samples = orig['DataPoints']
            chan_name = [x['Label'] for x in orig['ElectrodesInfo']]

            # we need these two items to read the data
            self.BOData = orig['BOData']
            self.factor = _convert_factor(orig['ElectrodesInfo'])

            nev_file = splitext(self.filename)[0] + '.nev'
            try:
                nev_orig = _read_neuralev(nev_file, trigger_bits=trigger_bits,
                                          trigger_zero=trigger_zero)[0]
            except FileNotFoundError:
                pass

            else:
                nev_orig.update(orig)  # precedence to orig
                orig = nev_orig

        elif file_header == b'NEURALSG':
            orig = _read_neuralsg(self.filename)
            s_freq = orig['SamplingFreq']
            n_samples = orig['DataPoints']

            # we need these two items to read the data
            self.BOData = orig['BOData']
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

        data = _read_nsx(self.filename, self.BOData, self.factor,
                         begsam, endsam)

        return data[chan, :]


def _read_nsx(filename, BOData, factor, begsam, endsam):
    """

    Common to NEURALCD and NEURALSG

    """
    n_chan = factor.shape[0]

    with open(filename, 'rb') as f:

        f.seek(BOData, SEEK_SET)
        f.seek(n_chan * 2 * begsam, SEEK_CUR)

        n_sam = endsam - begsam
        dat = fromfile(f, 'int16', n_chan * n_sam)
        dat = reshape(dat, (n_chan, n_sam), order='F')

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
        hdr['ChannelID'] = unpack('<I' * n_chan, f.read(4 * n_chan))

        BOData = f.tell()
        f.seek(0, SEEK_END)
        EOData = f.tell()

    # we read the time information from the corresponding NEV file
    nev_filename = splitext(filename)[0] + '.nev'
    with open(nev_filename, 'rb') as f:
        f.seek(28)
        time = unpack('<' + 'H' * 8, f.read(16))

    hdr['DateTimeRaw'] = time
    hdr['DateTime'] = datetime(time[0], time[1], time[3],
                               time[4], time[5], time[6], time[7])

    hdr['DataPoints'] = int((EOData - BOData) / (n_chan * 2))
    hdr['BOData'] = BOData

    return hdr


def _read_neuralcd(filename):
    """

    Notes
    -----
    For some reason, the time stamps are stored in UTC here (but in local
    time in the NEV file). So we need to take that into account

    """
    hdr = {}
    with open(filename, 'rb') as f:
        hdr['FileTypeID'] = f.read(8).decode('utf-8')

        BasicHdr = f.read(306)
        filespec = unpack('bb', BasicHdr[0:2])
        hdr['FileSpec'] = str(filespec[0]) + '.' + str(filespec[1])
        hdr['HeaderBytes'] = unpack('<I', BasicHdr[2:6])[0]
        hdr['SamplingLabel'] = _str(BasicHdr[6:22].decode('utf-8'))
        # hdr['Comment'] = _str(BasicHdr[22:278].decode('utf-8'))
        hdr['TimeRes'] = unpack('<I', BasicHdr[282:286])[0]
        hdr['SamplingFreq'] = int(hdr['TimeRes'] /
                                  unpack('<i', BasicHdr[278:282])[0])
        time = unpack('<' + 'H' * 8, BasicHdr[286:302])
        hdr['DateTimeRaw'] = time
        d = datetime(time[0], time[1], time[3], time[4], time[5], time[6],
                     time[7], utc)
        hdr['DateTime'] = d.astimezone(Eastern).replace(tzinfo=None)
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

        # TODO: allow for paused files, if they exist
        # "Added by NH - Feb 19, 2014" seems incorrect to me about BOData

        while f.tell() < EOF:

            if f.tell() < EOF and unpack('<B', f.read(1))[0] != 1:
                hdr['DataPoints'] = int((EOF - BOData) / (n_chan * 2))
                break

            Timestamp = unpack('<I', f.read(4))[0]
            DataPoints = unpack('<I', f.read(4))[0]
            BOData = f.tell()
            f.seek(DataPoints * n_chan * 2, SEEK_CUR)
            EOData = f.tell()
            hdr['DataPoints'] = int((EOData - BOData) / (n_chan * 2))

        hdr['BOData'] = BOData

    return hdr


def _read_neuralev(filename, trigger_bits=16, trigger_zero=True):
    """Read some information from NEV

    Parameters
    ----------
    filename : str
        path to NEV file
    trigger_bits : int, optional
        8 or 16, read the triggers as one or two bytes
    trigger_zero : bool, optional
        read the trigger zero or not

    Returns
    -------
    MetaTags : list of dict
        which corresponds to MetaTags of openNEV
    ElectrodesInfo : list of dict
        which corresponds to ElectrodesInfo of openNEV
    IOLabels : list of dict
        which corresponds to IOLabels of openNEV, however our version is not
        ordered, but you need to check Mode

    Notes
    -----
    The conversion to DateTime in openNEV.m is not correct. They add a value of
    2 to the day. Instead, they should add it to the index of the weekday

    It returns triggers as strings (format of EDFBrowser), but it does not read
    the othe types of events (waveforms, videos, etc).
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
        hdr['DateTime'] = datetime(time[0], time[1], time[3],
                                   time[4], time[5], time[6], time[7])
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

        if countDataPacket:

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
                raise NotImplementedError('Code not implemented to read ' +
                                          'PacketID ' +
                                          not_serialdigital[0]['packetID'])

            # convert to notes
            s_all = []
            for val in DigiValues:
                time = hdr['DateTime'] + timedelta(seconds=val['timestamp'] /
                                                   hdr['SampleRes'])
                s = (datetime.strftime(time, '%Y-%m-%dT%H:%M:%S.%f') + ',' +
                     '0' + ',' +  # zero duration
                     str(val['tempDigiVals']))
                s_all.append(s)

            hdr['notes'] = '\n'.join(s_all)

    return hdr, ElectrodesInfo, IOLabels


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
