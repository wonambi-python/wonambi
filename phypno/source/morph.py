from copy import deepcopy
from os.path import dirname, split

from numpy import arange, atleast_2d, squeeze
from mne import morph_data, SourceEstimate


class Morph:
    def __init__(self, from_surf, to_surf='fsaverage', smooth=None):
        self.from_surf = from_surf
        self.to_surf = to_surf
        self.smooth = smooth

    def __call__(self, data):

        output = deepcopy(data)

        from_surf_file = dirname(dirname(self.from_surf.surf_file))
        SUBJECTS_DIR, from_surf_name = split(from_surf_file)

        if 'lh' in self.from_surf.surf_file:  # TODO: not good, we need to check
            vertices = [arange(data.data[0].shape[0]), arange(0)]
        else:
            vertices = [arange(0), arange(data.data[0].shape[0])]

        stc = SourceEstimate(atleast_2d(data.data[0]).T, vertices=vertices,
                             tstep=0, tmin=0)
        m = morph_data(from_surf_name, self.to_surf, stc,
                       subjects_dir=SUBJECTS_DIR, grade=None,
                       smooth=self.smooth, verbose=False)

        output.data[0] = squeeze(m.data, axis=1)
        output.axis['surf'][0] = arange(m.data.shape[0])

        return output
