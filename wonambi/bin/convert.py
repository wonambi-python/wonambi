from argparse import ArgumentParser
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG
from pathlib import Path
from re import search
from textwrap import dedent

from numpy import isnan, array
from scipy.io.wavfile import write

from .. import __version__
from ..dataset import Dataset
from ..trans import resample
from ..ioeeg import (
    write_brainvision,
    write_edf,
    write_fieldtrip,
    write_bids,
    )

lg = getLogger('wonambi')


def main():
    parser = ArgumentParser(prog='won_convert', description=dedent("""\
    Convert data from one known format to another format

    NOTE
    You can convert to audio file (.wav). Specify the file name ending in '.wav'.
    The name of each channel will be appended to the file name.
    """))
    parser.add_argument('-v', '--version', action='store_true',
                        help='Return version')
    parser.add_argument('-l', '--log', default='info',
                        help='Logging level: info (default), debug')
    parser.add_argument('infile', nargs='?',
                        help='full path to dataset to convert')
    parser.add_argument('outfile', nargs='?',
                        help='full path of the output file with extension (.edf, .wav)')
    parser.add_argument('-b', '--begtime', default=None, type=float,
                        help='start time in seconds from the beginning of the recordings')
    parser.add_argument('-e', '--endtime', default=None, type=float,
                        help='end time in seconds from the beginning of the recordings')
    parser.add_argument('-r', '--rename', default=None,
            help='Rename the channels using the format specified here. For example, you can do -r "EEG chan{:03d}" where d is the channel index')
    parser.add_argument('-f', '--sampling_freq', default=None, type=float,
                        help='resample to this frequency (in Hz)')

    args = parser.parse_args()

    DATE_FORMAT = '%H:%M:%S'
    if args.log[:1].lower() == 'i':
        lg.setLevel(INFO)
        FORMAT = '{asctime:<10}{message}'

    elif args.log[:1].lower() == 'd':
        lg.setLevel(DEBUG)
        FORMAT = '{asctime:<10}{levelname:<10}{filename:<40}(l. {lineno: 6d})/ {funcName:<40}: {message}'

    formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT, style='{')
    handler = StreamHandler()
    handler.setFormatter(formatter)

    lg.handlers = []
    lg.addHandler(handler)

    if args.version:
        lg.info('WONAMBI v{}'.format(__version__))
        return

    if args.infile is None:
        raise ValueError('You need to specify the input file')
    if args.outfile is None:
        raise ValueError('You need to specify the output file')

    d = Dataset(args.infile)
    data = d.read_data(
        begtime=args.begtime,
        endtime=args.endtime,
        )

    if args.rename is not None:
        """
        m = search('(.*)[\'"]', args.rename)
        if m is None:
            raise ValueError(f'Could not parse the pattern {args.rename}')
        pattern = m.group(1)
        """
        pattern = args.rename
        lg.info(f'Renaming the channels with pattern: {pattern}')
        chan_names = [pattern.format(x + 1) for x in range(data.number_of('chan')[0])]
        data.axis['chan'][0] = array(chan_names)

    if args.sampling_freq is not None:
        lg.info(f'Resampling to {args.sampling_freq}')
        data = resample(data, s_freq=args.sampling_freq)

    outfile = Path(args.outfile)
    if outfile.suffix == '.edf':
        write_edf(
            data,
            outfile,
            physical_max=8191.75,  # so that precision is 0.25
            )

    elif outfile.suffix == '.wav':
        for i, chan in enumerate(data.axis['chan'][0]):
            wav_file = str(outfile.with_suffix('')) + '_' + chan + '.wav'
            x = data.data[0][i, :]
            x[isnan(x)] = 0
            x = (x - x.min()) / (x.max() - x.min()) * 2 - 1
            write(wav_file, data.s_freq, x)

    else:
        raise ValueError(f'Cannot convert to {outfile.suffix}')
