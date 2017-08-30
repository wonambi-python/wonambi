#!/usr/bin/env python3

from argparse import ArgumentParser
from os import environ
from pathlib import Path
from shutil import copyfile, rmtree
from subprocess import run
from sys import exit
from urllib.request import urlretrieve
from zipfile import ZipFile


parser = ArgumentParser(prog='setup_wonambi',
                        description='Run tests and documentation for wonambi')
parser.add_argument('-r', '--release', action='store_true',
                    help='create a point release')
parser.add_argument('-m', '--major_release', action='store_true',
                    help='create a major release')
parser.add_argument('-g', '--get_files', action='store_true',
                    help='download datasets to run tests')
parser.add_argument('-t', '--tests', action='store_true',
                    help='run tests')
parser.add_argument('-d', '--docs', action='store_true',
                    help='create documentations (run tests first)')
parser.add_argument('-c', '--clean', action='store_true',
                    help='clean up docs (including intermediate files)')
parser.add_argument('--clean_all', action='store_true',
                    help='clean up docs (--clean) and files for tests')

args = parser.parse_args()


BASE_PATH = Path(__file__).resolve().parent
DOCS_PATH = BASE_PATH / 'docs'
BUILD_PATH = DOCS_PATH / 'build'
SOURCE_PATH = DOCS_PATH / 'source'
# this is where the documentation has been built (needs to match travis deploy)
HTML_PATH = BUILD_PATH / 'html'
API_PATH = SOURCE_PATH / 'api'
GUI_PATH = SOURCE_PATH / 'gui' / 'images'
VIZ_PATH = SOURCE_PATH / 'viz' / 'images'
TEST_PATH = BASE_PATH / 'tests'
COV_PATH = BASE_PATH / 'htmlcov'
DATA_PATH = TEST_PATH / 'data'
DATA_PATH.mkdir(exist_ok=True)
if environ.get('CI', False):
    DOWNLOADS_PATH = Path(environ['DOWNLOADS'])  # cached dir in travis
else:
    DOWNLOADS_PATH = TEST_PATH / 'downloads'  # local
DOWNLOADS_PATH.mkdir(exist_ok=True)
print('Files stored in cached ' + str(DOWNLOADS_PATH.resolve()) + ':\n\t' +
      '\n\t'.join(str(x) for x in DOWNLOADS_PATH.iterdir()))

VER_PATH = BASE_PATH / 'wonambi' / 'VERSION'
CHANGES_PATH = BASE_PATH / 'CHANGES.rst'

REMOTE_FILES = [
    {'filename': 'PSG.edf',
     'url': 'https://www.physionet.org/pn4/sleep-edfx/SC4031E0-PSG.edf',
     'cached': 'SC4031E0-PSG.edf',
     'zipped': None,
     },
    {'filename': 'edfbrowser_generated_2.edf',
     'url': 'http://www.teuniz.net/edf_bdf_testfiles/test_generator_2_edfplus.zip',
     'cached': 'test_generator_2_edfplus.zip',
     'zipped': 'test_generator_2.edf',
     },
    {'filename': 'blackrock.ns4',
     'url': 'http://blackrockmicro.com/wp-content/uploads/2016/06/sampledata.zip',
     'cached': 'sampledata.zip',
     'zipped': 'sampleData/sampleData.ns4',
     },
    {'filename': 'bci2000.dat',
     'url': ['svn',
             'export',
             'http://www.bci2000.org/svn/trunk/data/samplefiles/eeg3_2.dat',
             str(DOWNLOADS_PATH / 'eeg3_2.dat'),
             '--username',
             environ.get('BCI2000_USER', ''),
             '--password',
             environ.get('BCI2000_PASSWORD', ''),
             '--no-auth-cache',
             ],
     'cached': 'eeg3_2.dat',
     'zipped': None,
     },
    {'filename': 'Public',
     'url': environ.get('DATA_URL'),
     'cached': 'personal.zip',
     'zipped': True,
     },
    ]


def _new_version(level):

    # read current version (and changelog)
    with VER_PATH.open() as f:
        major, minor = f.read().rstrip('\n').split('.')
        major, minor = int(major), int(minor)

    with CHANGES_PATH.open() as f:
        changes = f.read().split('\n')

    # update version (if major, reset minor)
    if level == 'major':
        major += 1
        minor = 1
    elif level == 'minor':
        minor += 1
    version = '{:d}.{:02d}'.format(major, minor)

    # ask user for comment
    comment = input('Comment for {} release v{}: '.format(level, version))
    if comment == '':
        print('empty comment, aborted')
        return

    # update change log
    ver_comment = '- **' + version + '**: ' + comment

    if level == 'major':
        marker = '=========='
        TO_ADD = ['Version ' + str(major),
                  '----------',
                  ver_comment,
                  '',
                  ]

    elif level == 'minor':
        marker = '----------'
        TO_ADD = [ver_comment,
                  ]

    index = changes.index(marker) + 1
    changes = changes[:index] + TO_ADD + changes[index:]
    with CHANGES_PATH.open('w') as f:
        f.write('\n'.join(changes))

    with VER_PATH.open('w') as f:
        f.write(version + '\n')

    return version, comment


def _release(level):
    """TODO: we should make sure that we are on master release"""
    version, comment = _new_version(level)

    if version is not None:

        run(['git',
             'commit',
             str(VER_PATH.relative_to(BASE_PATH)),
             str(CHANGES_PATH.relative_to(BASE_PATH)),
             '--amend',
             '--no-edit',
             ])
        run(['git',
             'tag',
             '-a',
             'v' + version,
             '-m',
             '"' + comment + '"',
             ])
        run(['git',
             'push',
             'origin',
             '--tags',
             ])
        run(['git',
             'push',
             'origin',
             'master',
             '-f',
             ])


def _get_files():
    """General script to download file from online sources. Each remote file
    should be specified in the list of dict REMOTE_FILES. Each entry in
    REMOTE_FILES contains:
    filename : the filename which is used by the test scripts
    cached : the filename which is stored in the cache directory
    url : the remote url. If str, it's a direct download. If it's a list, it's
    run as a command.
    zipped : if None, then the file is not zipped. If True, it extracts all
    the files (but be careful about the folder name). If str, it extracts only
    that specific file.

    Returns
    -------
    returncode : int
        code to send to shell (TODO: make sure you get 1 with exceptions)
    """
    for remote in REMOTE_FILES:

        final_file = DATA_PATH / remote['filename']

        if not final_file.exists():
            temp_file = DOWNLOADS_PATH / remote['cached']

            if not temp_file.exists():
                if remote['url'] is None:
                    print('missing URL, please contact developers')
                    return 1

                elif isinstance(remote['url'], list):
                    print('Running: ' + ' '.join(remote['url']))
                    run(remote['url'])
                else:
                    print('Downloading from ' + remote['url'])
                    urlretrieve(remote['url'], temp_file)

            if remote['zipped'] is None:
                print('Copying ' + str(temp_file) + ' to ' + str(final_file))
                copyfile(temp_file, final_file)  # or maybe symlink

            elif remote['zipped'] is True:  # explicit testing
                with ZipFile(temp_file) as zf:
                    print('Extracting all files in ' + remote['cached'] + ':\n\t' + '\n\t'.join(zf.namelist()))
                    zf.extractall(path=DATA_PATH)

            else:
                print('Extracting file ' + remote['zipped'] + ' to ' +
                      str(final_file))
                with ZipFile(temp_file) as zf:
                    extracted = Path(zf.extract(remote['zipped'], path=DOWNLOADS_PATH))
                    extracted.rename(final_file)

    return 0


def _tests():
    CMD = ['pytest',
           '--cov=wonambi',
           'tests',
           ]

    # html report if local
    if not environ.get('CI', False):
        CMD.insert(1, '--cov-report=html')

    output = run(CMD)
    return output.returncode


def _docs():
    print(BUILD_PATH)
    output = run(['sphinx-build',
                  '-T',
                  '-b',
                  'html',
                  '-d',
                  str(BUILD_PATH / 'doctrees'),
                  str(SOURCE_PATH),
                  str(HTML_PATH),
                  ])
    return output.returncode


def _clean_docs():
    rmtree(BUILD_PATH, ignore_errors=True)
    rmtree(API_PATH, ignore_errors=True)
    rmtree(GUI_PATH, ignore_errors=True)
    rmtree(VIZ_PATH, ignore_errors=True)

    # also remove coverage folder
    rmtree(COV_PATH, ignore_errors=True)


def _clean_download():
    pass


if __name__ == '__main__':
    returncode = 0

    if args.clean:
        _clean_docs()

    if args.clean_all:
        _clean_docs()
        _clean_download()

    if args.get_files:
        returncode = _get_files()

    if args.tests:
        returncode = _tests()

    if args.docs:
        returncode = _docs()

    if args.release:
        _release('minor')

    if args.major_release:
        _release('major')

    exit(returncode)
