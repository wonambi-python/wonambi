from logging import getLogger, FileHandler, DEBUG
from os.path import join, basename, splitext
from subprocess import check_output
from sys import version_info


git_ver = check_output("git --git-dir=../.git log |  awk 'NR==1' | "
                       "awk '{print $2}'",
                       shell=True).decode('utf-8').strip()

log_dir = '/home/gio/tools/phypno/test/log'
log_file = join(log_dir, splitext(basename(__file__))[0] + '_v' +
                str(version_info[0]) + '.log')
lg = getLogger('phypno')
lg.setLevel(DEBUG)
h_lg = FileHandler(log_file, mode='w')
lg.addHandler(h_lg)
lg.info('phypno ver: ' + git_ver)


#-----------------------------------------------------------------------------#
from phypno.attr.anat import import_freesurfer_LUT


def test_01_import_freesurfer_LUT():
    lg.info('---\nfunction: ' + __name__)
    import_freesurfer_LUT()

def test_02_import_freesurfer_LUT():
    lg.info('---\nfunction: ' + __name__)
    import_freesurfer_LUT('/opt/freesurfer/FreeSurferColorLUT.txt')

