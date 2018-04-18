"""Tests for the FOOOF fit object and methods.

Forked from https://github.com/voytekresearch/fooof

NOTES
-----
The tests here are not strong tests for accuracy.
    They serve rather as 'smoke tests', for if anything fails completely.
"""

from py.test import raises

import numpy as np

from wonambi.utils import FOOOF
from wonambi.utils.fooof.synth import gen_power_spectrum
from wonambi.utils.fooof.core.modutils import get_obj_desc
from wonambi.utils.fooof.core.utils import group_three

###################################################################################################
###################################################################################################

def test_fooof():
    """Check FOOOF object initializes properly."""

    assert FOOOF()

def test_fooof_fit_nk():
    """Test FOOOF fit, no knee."""

    bgp = [50, 2]
    gauss_params = [10, 0.5, 2, 20, 0.3, 4]

    xs, ys = gen_power_spectrum([3, 50], bgp, gauss_params)

    tfm = FOOOF()
    tfm.fit(xs, ys)

    # Check model results - background parameters
    assert np.all(np.isclose(bgp, tfm.background_params_, [0.5, 0.1]))

    # Check model results - gaussian parameters
    for ii, gauss in enumerate(group_three(gauss_params)):
        assert np.all(np.isclose(gauss, tfm._gaussian_params[ii], [1.5, 0.25, 0.5]))

def test_fooof_fit_knee():
    """Test FOOOF fit, with a knee."""

    bgp = [50, 2, 1]
    gauss_params = [10, 0.5, 2, 20, 0.3, 4]

    xs, ys = gen_power_spectrum([3, 50], bgp, gauss_params)

    tfm = FOOOF(background_mode='knee')
    tfm.fit(xs, ys)

    # Note: currently, this test has no accuracy checking at all
    assert True


def test_fooof_checks():
    """Test various checks, errors and edge cases in FOOOF."""

    xs, ys = gen_power_spectrum([3, 50], [50, 2], [10, 0.5, 2])

    tfm = FOOOF()

    # Check dimension error
    with raises(ValueError):
        tfm.fit(xs, np.reshape(ys, [1, len(ys)]))

    # Check shape mismatch error
    with raises(ValueError):
        tfm.fit(xs[:-1], ys)

    # Check trim_spectrum range
    tfm.fit(xs, ys, [3, 40])

    # Check freq of 0 issue
    xs, ys = gen_power_spectrum([3, 50], [50, 2], [10, 0.5, 2])
    tfm.fit(xs, ys)
    assert tfm.freqs[0] != 0

    # Check fit, and string report model error (no data / model fit)
    tfm = FOOOF()
    with raises(ValueError):
        tfm.fit()

def test_copy():
    """Test copy FOOOF method."""

    tfm = FOOOF()
    ntfm = tfm.copy()

    assert tfm != ntfm

def test_fooof_fit_failure():
    """Test that fit handles a failure."""

    # Use a new FOOOF, that is monkey-patched to raise an error
    #  This mimicks the main fit-failure, without requiring bad data / waiting for it to fail.
    tfm = FOOOF()
    def raise_runtime_error(*args, **kwargs):
        raise RuntimeError('Test-MonkeyPatch')
    tfm._fit_peaks = raise_runtime_error

    # Run a FOOOF fit - this should raise an error, but continue in try/except
    tfm.fit(*gen_power_spectrum([3, 50], [50, 2], [10, 0.5, 2, 20, 0.3, 4]))

    # Check after failing out of fit, all results are reset
    for result in get_obj_desc()['results']:
        cur_res = getattr(tfm, result)
        assert cur_res is None or np.all(np.isnan(cur_res))
