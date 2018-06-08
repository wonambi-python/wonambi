from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'wonambi', 'VERSION')) as f:
    VERSION = f.read().strip('\n')  # editors love to add newline

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='wonambi',
    version=VERSION,
    description='Tools for EEG, ECoG, iEEG, especially for sleep',
    long_description=long_description,
    url='https://github.com/wonambi-python/wonambi',
    author="Gio Piantoni / Jordan O'Byrne",
    author_email='wonambi@gpiantoni.com',
    license='GPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Scientific/Engineering :: Visualization',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='neuroscience analysis sleep EEG ECoG',
    packages=find_packages(exclude=('test', )),
    install_requires=[
        'numpy',
        'scipy',
        ],
    extras_require={
        'gui': [
            'pyqt5',
            ],
        'viz': [
            'vispy',
            ],
        'test': [  # to run tests
            'pytest',
            'pytest-qt',
            'pytest-cov',
            'codecov',
            'plotly',
            ],
        'all': [
            'pyqt5',
            'python-vlc',  # for videos, to avoid problems with backends
            'vispy',
            'h5py',
            'mne',
            'nibabel',
            'fooof',
            ]
    },
    package_data={
        'wonambi': [
            'widgets/icons/oxygen/*.png',
            'widgets/icons/wonambi.jpg',
            'VERSION',
            ],
    },

    entry_points={
        'console_scripts': [
            'wonambi=wonambi.scroll_data:main',
        ],
    },
)
