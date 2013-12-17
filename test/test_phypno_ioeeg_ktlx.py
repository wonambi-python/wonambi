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
from os.path import join
from phypno.ioeeg import Ktlx
from phypno.ioeeg.ktlx import _read_ent, _read_etc, _read_snc

ktlx_dir = '/home/gio/recordings/MG65/eeg/raw/MG65_eeg_sessA_d01_06_39_33'


def test_read_ent():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_ent(join(k.filename, k._basename + '.ent'))

def test_read_etc():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_etc(join(k.filename, k._basename + '.etc'))

def test_read_snc():
    lg.info('---\nfunction: ' + stack()[0][3])
    k = Ktlx(ktlx_dir)
    _read_snc(join(k.filename, k._basename + '.snc'))

