"""Module to read and return anatomical information, such as:
    - surfaces, with class Surf

"""
from collections import Counter
from logging import getLogger
from os import environ
from os.path import exists, join

from nibabel.freesurfer import read_geometry, read_annot
from numpy import array, empty, vstack, around, dot, append, reshape, meshgrid

from ..utils.caching import read_seg

lg = getLogger(__name__)

FS_AFFINE = array([[-1, 0, 0, 128],
                   [0, 0, -1, 128],
                   [0, 1, 0, 128],
                   [0, 0, 0, 1]])


def _find_neighboring_regions(pos, mri_dat, region, approx):

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
    regions = [x for x in regions if not 'White' in x and
               not 'Unknown' in x and not 'WM' in x]

    return regions


def import_freesurfer_LUT(fs_lut=None):
    """Import Look-up Table with colors and labels for anatomical regions.

    It's necessary that Freesurfer is installed and that the environmental
    variable 'FREESURFER_HOME' is present.

    Parameters
    ----------
    fs_lut : str
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
    else:
        try:
            fs_home = environ['FREESURFER_HOME']
        except KeyError:
            raise EnvironmentError('Freesurfer is not installed or '
                                   'FREESURFER_HOME is not defined as '
                                   'environmental variable')
        else:
            fs_lut = join(fs_home, 'FreeSurferColorLUT.txt')
            lg.info('Reading lookuptable in FREESURFER_HOME {}'.format(fs_lut))

    idx = []
    label = []
    rgba = empty((0, 4))
    with open(fs_lut, 'r') as f:
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
    freesurfer_dir : str
        subject-specific directory created by freesurfer
    hemi : str
            'lh' or 'rh'
    surf_type : str
        'pial', 'smoothwm', 'inflated', 'white', or 'sphere'

    Attributes
    ----------
    vert : numpy.ndarray
        vertices of the mesh
    tri : numpy.ndarray
        triangulation of the mesh

    """

    def __init__(self, freesurfer_dir, hemi, surf_type='pial'):
        fs = Freesurfer(freesurfer_dir)
        try:
            self.vert, self.tri = fs.read_surf(hemi, surf_type)
        except ValueError:
            raise NotImplementedError('Nibabel/read_geometry throws an error '
                                      'about reshape in Python 3 only')


class Freesurfer:
    """Provide class Freesurfer, with the information from freesurfer.

    Parameters
    ----------
    freesurfer_dir : str
        subject-specific directory created by freesurfer
    fs_lut : str
        path to file called FreeSurferColorLUT.txt

    Notes
    -----
    It's necessary that Freesurfer is installed and that the environmental
    variable 'FREESURFER_HOME' is present.

    """
    def __init__(self, freesurfer_dir, fs_lut=None):
        if not exists(freesurfer_dir):
            raise OSError(freesurfer_dir + ' does not exist')
        self.dir = freesurfer_dir
        try:
            lut = import_freesurfer_LUT(fs_lut)
            self.lookuptable = {'index': lut[0], 'label': lut[1],
                                'RGBA': lut[2]}
        except (IOError, OSError):  # IOError for 2.7, OSError for 3.3
            lg.warning('Could not find lookup table, some functions that rely '
                       'on it might complain or crash.')

    def find_brain_region(self, abs_pos, max_approx=0):
        """Find the name of the brain region in which an electrode is located.

        Parameters
        ----------
        abs_pos : numpy.ndarray
            3x0 vector with the position of interest.
        max_approx : int, optional
            max approximation to define position of the electrode.
        fs_lut : str
            path to file called FreeSurferColorLUT.txt

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

        """
        # convert to freesurfer coordinates of the MRI
        pos = around(dot(FS_AFFINE, append(abs_pos, 1)))[:3]
        lg.debug('Position in the MRI matrix: {}'.format(pos))

        mri_dat, _ = self.read_seg()

        for approx in range(max_approx + 1):
            lg.debug('Trying approx {}'.format(approx))
            regions = _find_neighboring_regions(pos, mri_dat,
                                                     self.lookuptable, approx)
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
        parc_file = join(self.dir, 'label', hemi + '.' + parc_type + '.annot')
        vert_val, region_color, region_name = read_annot(parc_file)
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
        seg_file = join(self.dir, 'mri', parc_type + '+aseg.mgz')
        return read_seg(seg_file)

    def read_surf(self, hemi, surf_type='pial'):
        """Read the surface for each hemisphere.

        Parameters
        ----------
        hemi : str
            'lh' or 'rh'
        surf_type : str
            'pial', 'smoothwm', 'inflated', 'white', or 'sphere'

        Returns
        -------
        numpy.ndarray
            vertices of the mesh
        numpy.ndarray
            triangulation of the mesh

        """
        surf_file = join(self.dir, 'surf', hemi + '.' + surf_type)
        surf_vert, surf_tri = read_geometry(surf_file)
        return surf_vert, surf_tri
