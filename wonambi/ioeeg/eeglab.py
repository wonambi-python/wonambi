from datetime import datetime
from numpy import c_, NaN, empty, memmap, float64
from pathlib import Path
from scipy.io import loadmat

from .utils import (read_hdf5_str,
                    read_hdf5_chan_name,
                    DEFAULT_DATETIME,
                    )
from ..utils import MissingDependency

try:
    from h5py import File
except ImportError as err:
    File = MissingDependency(err)


class EEGLAB:
    def __init__(self, filename):
        self.filename = Path(filename).resolve()

    def return_hdr(self):
        """
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
        self.fdtfile = None

        try:
            self.EEG = loadmat(str(self.filename), struct_as_record=False,
                               squeeze_me=True)['EEG']
            self.hdf5 = False

        except NotImplementedError:
            self.hdf5 = True

        if not self.hdf5:
            self.s_freq = self.EEG.srate
            chan_name = [chan.labels for chan in self.EEG.chanlocs]
            n_samples = self.EEG.pnts

            if isinstance(self.EEG.subject, str):
                subj_id = self.EEG.subject
            else:
                subj_id = ''
            try:
                start_time = datetime(*self.EEG.etc.T0)
            except AttributeError:
                start_time = DEFAULT_DATETIME

            if isinstance(self.EEG.datfile, str):
                self.fdtfile = self.EEG.datfile
            else:
                self.data = self.EEG.data

        else:

            with File(self.filename) as f:
                EEG = f['EEG']
                self.s_freq = EEG['srate'].value.item()
                chan_name = read_hdf5_chan_name(f, EEG['chanlocs']['labels'])
                n_samples = int(EEG['pnts'].value.item())

                subj_id = read_hdf5_str(EEG['subject'])
                try:
                    start_time = datetime(*EEG['etc']['T0'])
                except ValueError:
                    start_time = DEFAULT_DATETIME

                datfile = read_hdf5_str(EEG['datfile'])
                if datfile == '':
                    self.data = EEG['data'].value.T  # for some reason, you need to transpose this
                else:
                    self.fdtfile = datfile

        if self.fdtfile is not None:
            memshape = (len(chan_name), int(n_samples))
            memmap_file = self.filename.parent / self.fdtfile
            if not memmap_file.exists():
                renamed_memmap_file = self.filename.with_suffix('.fdt')
                if not renamed_memmap_file.exists():
                    raise FileNotFoundError(f'No file {memmap_file} or {renamed_memmap_file}')
                else:
                    memmap_file = renamed_memmap_file

            self.data = memmap(str(memmap_file), 'float32', mode='c', shape=memshape, order='F')

        return subj_id, start_time, self.s_freq, chan_name, n_samples, {}

    def return_dat(self, chan, begsam, endsam):
        n_samples = self.data.shape[1]

        dat = self.data[:, max((begsam, 0)):min((endsam, n_samples))].astype(float64)

        if begsam < 0:

            pad = empty((dat.shape[0], 0 - begsam))
            pad.fill(NaN)
            dat = c_[pad, dat]

        if endsam >= n_samples:

            pad = empty((dat.shape[0], endsam - n_samples))
            pad.fill(NaN)
            dat = c_[dat, pad]

        return dat[chan, :]

    def return_markers(self):
        markers = []

        if self.hdf5:
            from h5py import File
            with File(self.filename) as f:
                for evt, latency in zip(f['EEG']['event']['type'], f['EEG']['event']['latency']):
                    mrk_t = (f[latency[0]][0, 0] - 1) / self.s_freq

                    markers.append({
                        'name': str(f[evt[0]][0, 0]),
                        'start': mrk_t,
                        'end': mrk_t,
                        })
        else:

            for event in self.EEG.event:
                markers.append({
                    'name': str(event.type),
                    'start': (event.latency - 1) / self.s_freq,
                    'end': (event.latency - 1) / self.s_freq,
                })

        return markers
