"""Module to convert from electrode to sources using linear matrices

"""
from copy import deepcopy
from functools import partial
from logging import getLogger
from multiprocessing import Pool

from numpy import (arange, asarray, atleast_2d, empty, exp, isnan, NaN,
                   nansum)
from numpy.linalg import norm
try:
    from scipy.sparse import csr_matrix as sparse
    # test if csr_matrix is the fastest approach
except ImportError:
    sparse = lambda x: x

lg = getLogger(__name__)

gauss = lambda x, s: exp(-.5 * (x ** 2 / s ** 2))


class Linear:
    """
    TODO
    ----
    both hemispheres
    """
    def __init__(self, surf, chan, threshold=20, exponent=None, std=None):
        inverse = calc_xyz2surf(surf, chan.return_xyz(), threshold=threshold,
                                exponent=exponent, std=std)
        self.inv = sparse(inverse)
        self.chan = chan.return_label()

    def __call__(self, data, parameter='chan'):
        """

        TODO
        ----
        return_xyz should follow channel order
        """
        output = deepcopy(data)  # TODO: probably not the best way
        del output.axis[parameter]
        output.axis['surf'] = empty(data.number_of('trial'), dtype='O')
        output.data = empty(data.number_of('trial'), dtype='O')

        exclude_vert = ~asarray(self.inv.sum(axis=1)).flatten().astype(bool)

        for i, one_trl in enumerate(data):
            output.axis['surf'][i] = arange(self.inv.shape[0])
            output.data[i] = self.inv.dot(data.data[i])
            output.data[i][exclude_vert, ] = NaN

        return output


def calc_xyz2surf(surf, xyz, threshold=20, exponent=None, std=None):
    """Calculate transformation matrix from xyz values to vertices.

    Parameters
    ----------
    surf : instance of wonambi.attr.Surf
        the surface of only one hemisphere.
    xyz : numpy.ndarray
        nChan x 3 matrix, with the locations in x, y, z.
    std : float
        distance in mm of the Gaussian kernel
    exponent : int
        inverse law (1-> direct inverse, 2-> inverse square, 3-> inverse cube)
    threshold : float
        distance in mm for a vertex to pick up electrode activity (if distance
        is above the threshold, one electrode does not affect a vertex).

    Returns
    -------
    numpy.ndarray
        nVertices X xyz.shape[0] matrix

    Notes
    -----
    This function is a helper when plotting onto brain surface, by creating a
    transformation matrix from the values in space (f.e. at each electrode) to
    the position of the vertices (used to show the brain surface).

    There are many ways to move from values to vertices. The crucial parameter
    is the function at which activity decreases in respect to the distance. You
    can have an inverse relationship by specifying 'exponent'. If 'exponent' is
    2, then the activity will decrease as inverse square of the distance. The
    function can be a Gaussian. With std, you specify the width of the gaussian
    kernel in mm.
    For each vertex, it uses a threshold based on the distance ('threshold'
    value, in mm). Finally, it normalizes the contribution of all the channels
    to 1, so that the sum of the coefficients for each vertex is 1.

    You can also create your own matrix (and skip calc_xyz2surf altogether) and
    pass it as attribute to the main figure.
    Because it's a loop over all the vertices, this function is pretty slow,
    but if you calculate it once, you can reuse it.
    We take advantage of multiprocessing, which speeds it up considerably.
    """
    if exponent is None and std is None:
        exponent = 1

    if exponent is not None:
        lg.debug('Vertex values based on inverse-law, with exponent ' +
                 str(exponent))
        funct = partial(calc_one_vert_inverse, xyz=xyz, exponent=exponent)
    elif std is not None:
        lg.debug('Vertex values based on gaussian, with s.d. ' + str(std))
        funct = partial(calc_one_vert_gauss, xyz=xyz, std=std)

    with Pool() as p:
        xyz2surf = p.map(funct, surf.vert)

    xyz2surf = asarray(xyz2surf)

    if exponent is not None:
        threshold_value = (1 / (threshold ** exponent))
        external_threshold_value = threshold_value
    elif std is not None:
        threshold_value = gauss(threshold, std)
        external_threshold_value = gauss(std, std) # this is around 0.607
    lg.debug('Values thresholded at ' + str(threshold_value))

    xyz2surf[xyz2surf < threshold_value] = NaN

    # here we deal with vertices that are within the threshold value but far
    # from a single electrodes, so those remain empty
    sumval = nansum(xyz2surf, axis=1)
    sumval[sumval < external_threshold_value] = NaN

    # normalize by the number of electrodes
    xyz2surf /= atleast_2d(sumval).T
    xyz2surf[isnan(xyz2surf)] = 0

    return xyz2surf


def calc_one_vert_inverse(one_vert, xyz=None, exponent=None):
    """Calculate how many electrodes influence one vertex, using the inverse
    function.

    Parameters
    ----------
    one_vert : ndarray
        vector of xyz position of a vertex
    xyz : ndarray
        nChan X 3 with the position of all the channels
    exponent : int
        inverse law (1-> direct inverse, 2-> inverse square, 3-> inverse cube)

    Returns
    -------
    ndarray
        one vector with values for one vertex
    """
    trans = empty(xyz.shape[0])
    for i, one_xyz in enumerate(xyz):
        trans[i] = 1 / (norm(one_vert - one_xyz) ** exponent)
    return trans


def calc_one_vert_gauss(one_vert, xyz=None, std=None):
    """Calculate how many electrodes influence one vertex, using a Gaussian
    function.

    Parameters
    ----------
    one_vert : ndarray
        vector of xyz position of a vertex
    xyz : ndarray
        nChan X 3 with the position of all the channels
    std : float
        distance in mm of the Gaussian kernel

    Returns
    -------
    ndarray
        one vector with values for one vertex
    """
    trans = empty(xyz.shape[0])
    for i, one_xyz in enumerate(xyz):
        trans[i] = gauss(norm(one_vert - one_xyz), std)
    return trans
