from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'readme.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='phypno',

    version='13.4.0',

    description='Tools for electrophysiology, especially for sleep',
    long_description=long_description,

    url='https://github.com/gpiantoni/phypno',

    author='Gio Piantoni',
    author_email='phypno@gpiantoni.com',

    license='GPLv3',

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='neuroscience analysis sleep EEG ECoG',

    packages=find_packages(exclude=['data', 'doc', 'test']),

    extras_require={
        'analysis': ['scipy'],
        'gui': ['scipy'],  # pyqt4
        'viz': ['pyqtgraph'],
        'test': ['coverage'],
        'all': ['scipy',
                'mne',
                'nibabel',
                'pyqtgraph',
                ]
    },

    package_data={
        'phypno': ['widgets/icons/oxygen/*.png'],
    },

    entry_points={
        'console_scripts': [
            'scroll_data=phypno.scroll_data:main',
        ],
    },
)
