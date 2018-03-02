"""Keep all the files of interest here.

Changing this file will clear the cache of appveyor.
"""
from pathlib import Path

test_path = Path(__file__).resolve().parent

# Data from publicly available datasets
DATA_PATH = test_path / 'data'
axon_abf_file = DATA_PATH / 'axon_abf.abf'
bci2000_file = DATA_PATH / 'bci2000.dat'
psg_file = DATA_PATH / 'PSG.edf'
micromed_file = DATA_PATH / 'micromed.TRC'
generated_file = DATA_PATH / 'edfbrowser_generated_2.edf'

gui_file = psg_file

# Data from private repository
SAMPLE_PATH = DATA_PATH / 'Public'

ANAT_PATH = SAMPLE_PATH / 'anat'
# subsampled version of T1.mgz, to be used as low-res template
template_mri_path = ANAT_PATH / 'T1_subsampled.nii.gz'

ANNOT_PATH = SAMPLE_PATH / 'annot'
chan_path = ANNOT_PATH / 'bert_chan_locs.csv'
annot_domino_path = ANNOT_PATH / 'domino_test_01_EE_stag.txt'
annot_fasst_path = ANNOT_PATH / 'fasst_ACT2007-sh.mat'
annot_alice_path = ANNOT_PATH / 'Staging_Alice.txt'
annot_compumedics_path = ANNOT_PATH / 'Staging_Compumedics.txt'
annot_remlogic_path = ANNOT_PATH / 'Staging_RemLogic.txt'
annot_sandman_path = ANNOT_PATH / 'Staging_Sandman.txt'
annot_psg_path = ANNOT_PATH / 'PSG_scores.xml'

FREESURFER_HOME = SAMPLE_PATH / 'freesurfer'
LUT_path = FREESURFER_HOME / 'FreeSurferColorLUT.txt'
fs_path = FREESURFER_HOME / 'subjects' / 'bert'
surf_path = fs_path / 'surf' / 'lh.pial'

SUBJECTS_DIR = SAMPLE_PATH / 'SUBJECTS_DIR'

IO_PATH = SAMPLE_PATH / 'io'
ktlx_file = IO_PATH / 'xltek'
mff_file = IO_PATH / 'egi.mff'
nev_file = IO_PATH / 'blackrock' / 'blackrock.nev'
ns2_file = IO_PATH / 'blackrock' / 'blackrock.ns2'
ns4_file = IO_PATH / 'blackrock' / 'sampleData.ns4'
hdf5_file = IO_PATH / 'fieldtrip_hdf5.mat'

# Folder where to export data
EXPORTED_PATH = test_path / 'exported'
EXPORTED_PATH.mkdir(exist_ok=True)
annot_file = EXPORTED_PATH / 'annot_scores.xml'
annot_export_file = EXPORTED_PATH / 'annot_scores.csv'
annot_fasst_export_file = EXPORTED_PATH / 'annot_fasst.xml'
annot_sleepstats_path = EXPORTED_PATH / 'annot_sleepstats.csv'
exported_chan_path = EXPORTED_PATH / 'grid_chan.sfp'
channel_montage_file = EXPORTED_PATH / 'channel_montage.json'
channel_montage_reref_file = EXPORTED_PATH / 'channel_montage_reref.json'
fieldtrip_file = EXPORTED_PATH / 'fieldtrip.mat'
wonambi_file = EXPORTED_PATH / 'exported.won'
svg_file = EXPORTED_PATH / 'graphics_svg'

# Store images
DOCS_PATH = test_path.parent / 'docs'
SOURCE_PATH = DOCS_PATH / 'source'
GUI_PATH = SOURCE_PATH / 'gui' / 'images'
GUI_PATH.mkdir(exist_ok=True)
VIZ_PATH = SOURCE_PATH / 'analysis' / 'images'
VIZ_PATH.mkdir(exist_ok=True)
PLOTLY_PATH = SOURCE_PATH / 'analysis' / 'plotly'
PLOTLY_PATH.mkdir(exist_ok=True)
