"""Module to read and return anatomical information, such as:
    - surfaces, with class Surf

"""
from os.path import exists, join, splitext
from nibabel import load
from nibabel.freesurfer import read_geometry, read_annot


def detect_format(filename):
    """Detect file format of the channels based on extension.

    Parameters
    ----------
    filename : str
        name of the filename

    Returns
    -------
    str
        file format

    """
    if splitext(filename)[1] == '.csv':
        recformat = 'csv'
    else:
        recformat = 'unknown'

    return recformat


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
        self.vert, self.tri = fs.read_surf(hemi, surf_type)


class Freesurfer:
    """Provide class Freesurfer, with the information from freesurfer.

    Parameters
    ----------
    freesurfer_dir : str
        subject-specific directory created by freesurfer

    """

    def __init__(self, freesurfer_dir):
        if not exists(freesurfer_dir):
            raise IOError(freesurfer_dir + ' does not exist')
        self.dir = freesurfer_dir

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
            3d matrix
        numpy.ndarray
            4x4 affine matrix

        """
        seg_file = join(self.dir, 'mri', parc_type + '+aseg.mgz')
        seg_mri = load(seg_file)
        seg_aff = seg_mri.get_affine()
        seg_dat = seg_mri.get_data()
        return seg_dat, seg_aff

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
