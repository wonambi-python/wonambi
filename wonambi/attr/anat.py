"""Module to read and return anatomical information, such as:
    - surfaces, with class Surf
    - brains, with class BrainSurf (both hemispheres)
"""
from collections import Counter
from logging import getLogger
from os import environ
from pathlib import Path
from re import compile
from struct import unpack

from numpy import (array, empty, vstack, around, dot, append, reshape,
                   meshgrid, asarray)

lg = getLogger(__name__)

try:
    from nibabel.freesurfer import load, read_annot
    from nibabel import load as nload
except ImportError:
    pass

FS_AFFINE = array([[-1, 0, 0, 128],
                   [0, 0, -1, 128],
                   [0, 1, 0, 128],
                   [0, 0, 0, 1]])
HEMISPHERES = 'lh', 'rh'


def _read_geometry(surf_file):
    """Read a triangular format Freesurfer surface mesh.

    Parameters
    ----------
    surf_file : str
        path to surface file

    Returns
    -------
    coords : numpy.ndarray
        nvtx x 3 array of vertex (x, y, z) coordinates
    faces : numpy.ndarray
        nfaces x 3 array of defining mesh triangles

    Notes
    -----
    This function comes from nibabel, but it doesn't use numpy because numpy
    doesn't return the correct values in Python 3.
    """
    with open(surf_file, 'rb') as f:
        filebytes = f.read()

    assert filebytes[:3] == b'\xff\xff\xfe'
    i0 = filebytes.index(b'\x0A\x0A') + 2
    i1 = i0 + 4
    vnum = unpack('>i', filebytes[i0:i1])[0]
    i0 = i1
    i1 += 4
    fnum = unpack('>i', filebytes[i0:i1])[0]
    i0 = i1
    i1 += 4 * vnum * 3
    verts = unpack('>' + 'f' * vnum * 3, filebytes[i0:i1])
    i0 = i1
    i1 += 4 * fnum * 3
    faces = unpack('>' + 'i' * fnum * 3, filebytes[i0:i1])

    verts = asarray(verts).reshape(vnum, 3)
    faces = asarray(faces).reshape(fnum, 3)
    return verts, faces


def _find_neighboring_regions(pos, mri_dat, region, approx, exclude_regions):

    spot_size = approx * 2 + 1

    x, y, z = meshgrid(range(spot_size), range(spot_size), range(spot_size))
    neighb = vstack((reshape(x, (1, spot_size ** 3)),
                     reshape(y, (1, spot_size ** 3)),
                     reshape(z, (1, spot_size ** 3)))).T - approx
    regions = []
    for p in range(neighb.shape[0]):
        d_type = mri_dat[pos[0] + neighb[p, 0], pos[1] + neighb[p, 1],
                         pos[2] + neighb[p, 2]]
        label_index = region['index'].index(d_type)
        regions.append(region['label'][label_index])

    if exclude_regions:
        excluded = compile('|'.join(exclude_regions))
        regions = [x for x in regions if not excluded.search(x)]

    return regions


def import_freesurfer_LUT(fs_lut=None):
    """Import Look-up Table with colors and labels for anatomical regions.

    It's necessary that Freesurfer is installed and that the environmental
    variable 'FREESURFER_HOME' is present.

    Parameters
    ----------
    fs_lut : str or Path
        path to file called FreeSurferColorLUT.txt

    Returns
    -------
    idx : list of int
        indices of regions
    label : list of str
        names of the brain regions
    rgba : numpy.ndarray
        one row is a brain region and the columns are the RGB + alpha colors
    """
    if fs_lut is not None:
        lg.info('Reading user-specified lookuptable {}'.format(fs_lut))
        fs_lut = Path(fs_lut)
    else:
        try:
            fs_home = environ['FREESURFER_HOME']
        except KeyError:
            raise OSError('Freesurfer is not installed or FREESURFER_HOME is '
                          'not defined as environmental variable')
        else:
            fs_lut = Path(fs_home) / 'FreeSurferColorLUT.txt'
            lg.info('Reading lookuptable in FREESURFER_HOME {}'.format(fs_lut))

    idx = []
    label = []
    rgba = empty((0, 4))
    with fs_lut.open('r') as f:
        for l in f:
            if len(l) <= 1 or l[0] == '#' or l[0] == '\r':
                continue
            (t0, t1, t2, t3, t4, t5) = [t(s) for t, s in
                                        zip((int, str, int, int, int, int),
                                        l.split())]
            idx.append(t0)
            label.append(t1)
            rgba = vstack((rgba, array([t2, t3, t4, t5])))

    return idx, label, rgba


class Surf:
    """Provide class Surf, with the positions and connections of vertices.

    Parameters
    ----------
    surf_file : str or Path
        freesurfer file containing the surface

    Attributes
    ----------
    surf_file : path to file
        freesurfer file containing the surface
    vert : numpy.ndarray
        vertices of the mesh
    tri : numpy.ndarray
        triangulation of the mesh
    """
    def __init__(self, surf_file):
        self.surf_file = surf_file
        surf_vert, surf_tri = _read_geometry(self.surf_file)
        self.vert = surf_vert
        self.tri = surf_tri
        self.n_vert = surf_vert.shape[0]


class Brain:
    """Class that contains the left and right hemispheres.

    Parameters
    ----------
    freesurfer_dir : str
        subject-specific directory created by freesurfer
    surf_type : str
        'pial', 'smoothwm', 'inflated', 'white', or 'sphere'
    """
    def __init__(self, freesurfer_dir, surf_type='pial'):

        freesurfer_dir = Path(freesurfer_dir)

        for hemi in HEMISPHERES:
            surf_file = freesurfer_dir / 'surf' / (hemi + '.' + surf_type)
            setattr(self, hemi, Surf(surf_file))


class Freesurfer:
    """Provide class Freesurfer, with the information from freesurfer.

    Parameters
    ----------
    freesurfer_dir : str or Path
        subject-specific directory created by freesurfer
    fs_lut : str or Path
        path to file called FreeSurferColorLUT.txt

    Notes
    -----
    It's necessary that Freesurfer is installed and that the environmental
    variable 'FREESURFER_HOME' is present.
    """
    def __init__(self, freesurfer_dir, fs_lut=None):
        freesurfer_dir = Path(freesurfer_dir)
        if not freesurfer_dir.exists():
            raise OSError(str(freesurfer_dir) + ' does not exist')

        self.dir = freesurfer_dir
        try:
            lut = import_freesurfer_LUT(fs_lut)
            self.lookuptable = {'index': lut[0], 'label': lut[1],
                                'RGBA': lut[2]}
        except OSError as err:
            self.lookuptable = None
            lg.warning('Could not find lookup table (see below for explanation)'
                       '. Some functions that rely on it might complain or '
                       'crash.')
            lg.warning(err)

    @property
    def surface_ras_shift(self):
        """Freesurfer uses two coordinate systems: one for volumes ("RAS") and
        one for surfaces ("tkReg", "tkRAS", and "Surface RAS").
        To get from surface to volume coordinates, add this numbers.
        To get from volume to surface coordinates, substract this numbers.
        """
        T1_path = self.dir / 'mri' / 'T1.mgz'
        assert T1_path.exists()

        try:
            T1 = nload(str(T1_path))
        except NameError:
            raise ImportError('nibabel needs to be installed for this function')

        return T1.header['Pxyz_c']

    def find_brain_region(self, abs_pos, parc_type='aparc', max_approx=None,
                          exclude_regions=None):
        """Find the name of the brain region in which an electrode is located.

        Parameters
        ----------
        abs_pos : numpy.ndarray
            3x0 vector with the position of interest.
        parc_type : str
            'aparc', 'aparc.a2009s', 'BA', 'BA.thresh', or 'aparc.DKTatlas40'
            'aparc.DKTatlas40' is only for recent freesurfer versions
        max_approx : int, optional
            max approximation to define position of the electrode.
        exclude_regions : list of str or empty list
            do not report regions if they contain these substrings. None means
            that it does not exclude any region.

        Notes
        -----
        It determines the possible brain region in which one electrode is
        present, based on Freesurfer segmentation. You can imagine that
        sometimes one electrode is not perfectly located within one region,
        but it's a few mm away. The parameter "approx" specifies this tolerance
        where each value is one mm. It keeps on searching in larger and larger
        spots until it finds at least one region which is not white matter. If
        there are multiple regions, it returns the region with the most
        detection.
        Minimal value is 0, which means only if the electrode is in the
        precise location.

        If you want to exclude white matter regions with 'aparc', use
            exclude_regions = ('White', 'WM', 'Unknown')
        and with 'aparc.a2009s', use:
            exclude_regions = ('White-Matter')
        """
        # convert to freesurfer coordinates of the MRI
        pos = around(dot(FS_AFFINE, append(abs_pos, 1)))[:3].astype(int)
        lg.debug('Position in the MRI matrix: {}'.format(pos))

        mri_dat, _ = self.read_seg(parc_type)

        if max_approx is None:
            max_approx = 3

        for approx in range(max_approx + 1):
            lg.debug('Trying approx {} out of {}'.format(approx, max_approx))
            regions = _find_neighboring_regions(pos, mri_dat,
                                                self.lookuptable, approx,
                                                exclude_regions)
            if regions:
                break

        if regions:
            c_regions = Counter(regions)
            return c_regions.most_common(1)[0][0], approx
        else:
            return '--not found--', approx

    def read_label(self, hemi, parc_type='aparc'):
        """Read the labels (annotations) for each hemisphere.

        Parameters
        ----------
        hemi : str
            'lh' or 'rh'
        parc_type : str
            'aparc', 'aparc.a2009s', 'BA', 'BA.thresh', or 'aparc.DKTatlas40'
            'aparc.DKTatlas40' is only for recent freesurfer versions

        Returns
        -------
        numpy.ndarray
            value at each vertex, indicating the label
        numpy.ndarray
            RGB + alpha colors for each label
        list of str
            names of the labels
        """
        parc_file = self.dir / 'label' / (hemi + '.' + parc_type + '.annot')
        try:
            vert_val, region_color, region_name = read_annot(parc_file)
        except NameError:
            raise ImportError('nibabel needs to be installed for this function')
        region_name = [x.decode('utf-8') for x in region_name]
        return vert_val, region_color, region_name

    def read_seg(self, parc_type='aparc'):
        """Read the MRI segmentation.

        Parameters
        ----------
        parc_type : str
            'aparc' or 'aparc.a2009s'

        Returns
        -------
        numpy.ndarray
            3d matrix with values
        numpy.ndarray
            4x4 affine matrix
        """
        seg_file = self.dir / 'mri' / (parc_type + '+aseg.mgz')
        try:
            seg_mri = load(seg_file)
        except NameError:
            raise ImportError('nibabel needs to be installed for this function')
        seg_aff = seg_mri.affine
        seg_dat = seg_mri.get_data()
        return seg_dat, seg_aff

    def read_brain(self, surf_type='pial'):
        """Read the surface of both hemispheres.

        Parameters
        ----------
        surf_type : str
            'pial', 'smoothwm', 'inflated', 'white', or 'sphere'

        Returns
        -------
        instance of Brain
            the surfaces of both brain hemispheres
        """
        return Brain(self.dir, surf_type=surf_type)
