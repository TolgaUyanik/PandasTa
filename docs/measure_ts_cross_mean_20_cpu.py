# -*- coding: utf-8 -*-
"""TS-CROSS-MEAN-20: run `tests/test_ts_cross_mean_20.py` with numpy's
`AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list
issue-solver re-runs port test modules under, standing in for a GitHub
runner without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift
from what was actually turned off.

    python docs/measure_ts_cross_mean_20_cpu.py

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init,
so it has to be in the environment BEFORE numpy is imported -- hence this
file rather than a flag. It sets the variable, imports numpy (asserting
that the dispatch actually took), and runs the module's tests in process.

Why it matters here: the window sum and the two extrema are numpy
reductions and `np.log` is a numpy ufunc, and a different SIMD width
changes their last bits. This column then decides a COMPARISON on those
last bits, so a single flipped bit would move an integer count by up to 2
-- which is why the test module asserts BIT-equality against its oracles
rather than a tolerance, and why `test_scale_the_margin_that_makes_it_hold`
pins the margin (4.8e-08 of the window's own magnitude at worst, against an
ulp of 2.2e-16) that makes those bit-equalities survive a change of kernel.
This script is what turns "the margin is wide enough" into a run.
"""
import os
import sys

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402

if __name__ == "__main__":
    dispatch = np.core._multiarray_umath.__cpu_dispatch__ if hasattr(
        np.core._multiarray_umath, "__cpu_dispatch__") else []
    enabled = [f for f in dispatch
               if np.core._multiarray_umath.__cpu_features__.get(f)]
    print(f"numpy {np.__version__}")
    print(f"NPY_DISABLE_CPU_FEATURES = "
          f"{os.environ['NPY_DISABLE_CPU_FEATURES']!r}")
    print(f"dispatchable features still enabled: {enabled}")
    for feature in ("AVX512F", "AVX512_SKX", "AVX2", "FMA3"):
        if feature in enabled:
            raise SystemExit(f"{feature} is still enabled -- the environment "
                             f"edit did not take, so this run proves nothing")
    sys.exit(pytest.main(["tests/test_ts_cross_mean_20.py", "-q",
                          "--no-header"]))
