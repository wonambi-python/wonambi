from . import *

from os.path import join
from numpy import array
from numpy.random import random
from tempfile import mkdtemp

from phypno.attr import Freesurfer, Channels
from phypno.attr.chan import (detect_format, _convert_unit, Chan,
                              assign_region_to_channels, find_chan_in_region)
from phypno.utils.exceptions import UnrecognizedFormat

temp_dir = mkdtemp()
fs_dir = join(data_dir, 'MGXX/mri/proc/freesurfer')
elec_file = join(data_dir, 'MGXX/doc/elec/elec_pos_adjusted.csv')
random_file = join(data_dir, 'MGXX/doc/wiki/xltek_datasets')

mu = '\N{GREEK SMALL LETTER MU}'


def test_detect_format_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert detect_format(elec_file) == 'csv'


def test_detect_format_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    assert detect_format(random_file) == 'unknown'


def test_convert_unit():
    lg.info('---\nfunction: ' + stack()[0][3])
    unit = _convert_unit(None)
    assert unit == ''
    unit = _convert_unit('microvolt')
    assert unit == mu + 'V'
    unit = _convert_unit('microVolt')
    assert unit == mu + 'V'
    unit = _convert_unit('muV')
    assert unit == mu + 'V'
    unit = _convert_unit('mVolt')
    assert unit == 'mV'
    unit = _convert_unit('milliV')
    assert unit == 'mV'
    unit = _convert_unit('mVolt')
    assert unit == 'mV'
    unit = _convert_unit('mV')
    assert unit == 'mV'


def test_Chan_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Chan('chan001')


def test_Chan_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    Chan('chan001', [0, 0, 0])


def test_Chan_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    Chan('chan001', [0, 0, 0], 'microVolt')


def test_Chan_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Chan('chan001', [0, 0, 0], 'microVolt', {'region': 'cortex'})
    ch.attr.update({'region': 'hippo',
                    'type': 'grid'})


@raises(UnrecognizedFormat)
def test_Channels_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    Channels(random_file)


def test_Channels_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Channels(elec_file)
    assert ch.n_chan == 103
    assert_array_equal(ch.return_xyz(['FPS1']),
                       array([[-19.29,  67.92,  20.56]]))
    ch.export(join(temp_dir, 'elec_file.csv'))


@raises(ValueError)
def test_Channels_03():
    lg.info('---\nfunction: ' + stack()[0][3])
    chan_name = ['ch{0:03}'.format(x) for x in range(10)]
    xyz = random((10, 4))
    Channels(chan_name, xyz)

labels = ['ch{0:03}'.format(x) for x in range(10)]
xyz = random((10, 3))


def test_Channels_04():
    lg.info('---\nfunction: ' + stack()[0][3])
    Channels(labels, xyz)


ch = Channels(labels, xyz)


def test_Channels_05():
    lg.info('---\nfunction: ' + stack()[0][3])
    has00 = lambda x: '00' in x.label
    ch_with_00 = ch(has00)
    assert len(ch_with_00.chan) == 10

    has001 = lambda x: '001' in x.label
    chan_with_001 = ch(has001)
    assert len(chan_with_001.chan) == 1


def test_Channels_06():
    lg.info('---\nfunction: ' + stack()[0][3])
    labels = ch.return_label()
    assert len(labels) == ch.n_chan


@raises(TypeError)
def test_Channels_07():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch.return_label(['chan001'])


def test_Channels_08():
    lg.info('---\nfunction: ' + stack()[0][3])
    xyz = ch.return_xyz(['ch000', 'ch001'])
    assert xyz.shape == (2, 3)


@raises(ValueError)
def test_Channels_09():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch.return_xyz(['chXXX'])


def test_Channels_10():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch.return_xy()  # does nothing


def test_Channels_11():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch.chan[0].attr['region'] = 'hippo'
    region = ch.return_attr('region')
    assert region[0] == 'hippo'
    assert region[1] is None


@attr('slow')
def test_assign_region_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Channels(elec_file)
    fs = Freesurfer(fs_dir)
    ch = assign_region_to_channels(ch, fs)
    neuroport = ch(lambda x: x.label == 'neuroport').chan[0].attr['region']
    assert neuroport == 'ctx-lh-rostralmiddlefrontal'


@attr('slow')
def test_find_chan_in_region_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    ch = Channels(elec_file)
    fs = Freesurfer(fs_dir)
    cing_chan = find_chan_in_region(ch, fs, 'cingulate')
    assert cing_chan == ['LOF1', 'LOF2', 'LAF1', 'LAF2', 'LMF2']
