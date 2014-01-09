from inspect import stack
from logging import getLogger
from nose.tools import raises
from subprocess import check_output


lg = getLogger('phypno')
git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()
lg.info('phypno ver: ' + git_ver)
lg.info('Module: ' + __name__)

#-----------------------------------------------------------------------------#
from phypno import Dataset
from phypno.trans import Freq, TimeFreq


edf_file = '/home/gio/tools/phypno/test/data/sample.edf'
d = Dataset(edf_file)
data = d.read_data(chan=['LMF6'], begtime=0, endtime=10)


def test_freq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    calc_freq = Freq()
    fr = calc_freq(data)


@raises(TypeError)
def test_timefreq_01():
    lg.info('---\nfunction: ' + stack()[0][3])
    tf = TimeFreq()  # without toi
    tf(data)


def test_timefreq_02():
    lg.info('---\nfunction: ' + stack()[0][3])
    tf = TimeFreq(toi=range(2, 8))
    tf(data)
