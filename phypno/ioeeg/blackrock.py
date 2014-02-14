from datetime import datetime, timedelta
from os import SEEK_END
from os.path import splitext
from struct import unpack

from numpy.random import rand

HOUR_OFFSET = -4
DAY_OFFSET = 0


def _make_str(t_in):
    t_out = []
    for t in t_in:
        if t == b'\x00':
            break
        t_out.append(t.decode('utf-8'))
    return ''.join(t_out)


class BlackRock:
    """Basic class to read the data.

    Parameters
    ----------
    filename : path to file
        the name of the filename or directory

    Notes
    -----
    Check that the date and time is correct, by comparing with a known file.
    There seems to be something wrong with the date/time, nev and nsX don't
    correspond.

    """
    def __init__(self, filename):
        self.filename = filename

    def _read_neuralcd(self):

        hdr = {}
        with open(self.filename, 'rb') as f:
            hdr['FileTypeID'] = f.read(8).decode('utf-8')
            assert hdr['FileTypeID'] == 'NEURALCD'

            BasicHdr = f.read(306)
            filespec = unpack('bb', BasicHdr[0:2])
            hdr['FileSpec'] = str(filespec[0]) + '.' + str(filespec[1])
            hdr['HeaderBytes'] = unpack('<I', BasicHdr[2:6])[0]
            hdr['SamplingLabel'] = BasicHdr[6:22].decode('utf-8').strip('\x00')
            # hdr['Comment'] = BasicHdr[22:278].decode('utf-8').strip('\x00')
            hdr['TimeRes'] = unpack('<I', BasicHdr[282:286])[0]
            hdr['SamplingFreq'] = int(hdr['TimeRes'] /
                                      unpack('<i', BasicHdr[278:282])[0])
            time = unpack('<' + 'H' * 8, BasicHdr[286:302])
            hdr['DateTimeRaw'] = time
            hdr['DateTime'] = (datetime(time[0], time[1],
                                        time[3] + DAY_OFFSET,
                                        time[4], time[5], time[6]) +
                               timedelta(hours=HOUR_OFFSET))
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
                elec['ElectrodeID'] = unpack('H', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 16
                elec['Label'] = ExtHdr[i0:i1].decode('utf-8').strip('\x00')
                i0, i1 = i1, i1 + 1
                elec['ConnectorBank'] = chr(unpack('B', ExtHdr[i0:i1])[0] +
                                            ord('A') - 1)
                i0, i1 = i1, i1 + 1
                elec['ConnectorPin'] = unpack('B', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['MinDigiValue'] = unpack('h', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['MaxDigiValue'] = unpack('h', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['MinAnalogValue'] = unpack('h', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['MaxAnalogValue'] = unpack('h', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 16
                elec['AnalogUnits'] = ExtHdr[i0:i1].decode('utf-8').strip('\x00')
                i0, i1 = i1, i1 + 4
                elec['HighFreqCorner'] = unpack('I', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['HighFreqOrder'] = unpack('I', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['HighFilterType'] = unpack('H', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['LowFreqCorner'] = unpack('I', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 4
                elec['LowFreqOrder'] = unpack('I', ExtHdr[i0:i1])[0]
                i0, i1 = i1, i1 + 2
                elec['LowFilterType'] = unpack('H', ExtHdr[i0:i1])[0]
                ElectrodesInfo.append(elec)

            hdr['ElectrodesInfo'] = ElectrodesInfo

            EOexH = f.tell()
            f.seek(0, SEEK_END)
            EOF = f.tell()
            f.seek(EOexH)
            n_chan = hdr['ChannelCount']

            if f.tell() >= EOF:
                raise EOFError('File {0} does not seem to contain data '
                               '(size {1} B)'.format(self.filename, EOF))

            # TODO: allow for paused files, if they exist
            while f.tell() < EOF:
                Timestamp = unpack('I', f.read(4))[0]
                DataPoints = unpack('I', f.read(4))[0]
                BOData = f.tell()
                f.seek(DataPoints * n_chan * 2)
                EOData = f.tell()
                hdr['DataPoints'] = int((EOData - BOData) / (n_chan * 2))
                if f.tell() < EOF and unpack('B', f.read(1))[0] != 1:
                    hdr['DataPoints'] = int((EOF - BOData) / (n_chan * 2))
                    break

        return hdr

    def _read_neuralev(self):

        hdr = {}
        with open(self.filename, 'rb') as f:

            BasicHdr = f.read(336)

            i1 = 8
            hdr['FileTypeID'] = BasicHdr[:i1].decode('utf-8')
            assert hdr['FileTypeID'] == 'NEURALEV'
            i0, i1 = i1, i1 + 2
            filespec = unpack('bb', BasicHdr[i0:i1])
            hdr['FileSpec'] = str(filespec[0]) + '.' + str(filespec[1])
            i0, i1 = i1, i1 + 2
            hdr['Flags'] = unpack('H', BasicHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            hdr['HeaderOffset'] = unpack('I', BasicHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            hdr['PacketBytes'] = unpack('I', BasicHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            hdr['TimeRes'] = unpack('I', BasicHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 4
            hdr['SampleRes'] = unpack('I', BasicHdr[i0:i1])[0]
            i0, i1 = i1, i1 + 16
            time = unpack('<' + 'H' * 8, BasicHdr[i0:i1])
            hdr['DateTimeRaw'] = time
            hdr['DateTime'] = datetime(time[0], time[1],
                                       time[3] + DAY_OFFSET,
                                       time[4], time[5], time[6])
            i0, i1 = i1, i1 + 32
            # hdr['Application'] = BasicHdr[i0:i1].decode('utf-8')
            i0, i1 = i1, i1 + 256
            # hdr['Comment'] = BasicHdr[i0:i1].decode('utf-8')

            f.seek(-hdr['PacketBytes'], SEEK_END)
            hdr['DataDuration'] = unpack('I', f.read(4))[0]

        return hdr

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
        ext = splitext(self.filename)[1]
        if ext[:3] == '.ns':
            orig = self._read_neuralcd()
            s_freq = orig['SamplingFreq']
            n_samples = orig['DataPoints']
            chan_name = [x['Label'] for x in orig['ElectrodesInfo']]

        elif ext == '.nev':
            orig = self._read_neuralev()
            s_freq = orig['SampleRes']
            n_samples = orig['DataDuration']
            chan_name = ['dummy', ]

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
        data = rand(10, 100)
        return data[chan, begsam:endsam]
