# -*- coding: utf-8 -*-
"""TS-Q05-60: run `tests/test_ts_q05_60.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift
from what was actually turned off.

    python docs/measure_ts_q05_60_cpu.py

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init,
so it has to be in the environment BEFORE numpy is imported -- hence this
file rather than a flag. It sets the variable, imports numpy (asserting
that the dispatch actually took), and runs the module's tests in process.

Why it matters here, and why the exposure is SMALL. The frames are built
with `np.exp` and `np.cumsum`, which are dispatched, so the generated
closes themselves can differ in their last bits between kernels -- any
assertion on an exact COUNT of distinct values or of caught offsets is
therefore a band in `tests/test_ts_q05_60.py` and not a target. What the
column itself does is a division, a sort and one blend of two order
statistics: the division is IEEE-exact whatever the kernel, and pandas'
`roll_quantile` is a Cython skiplist rather than a numpy reduction, so the
bit-equalities this module's Gate A and Gate D rest on (the x8/x64
rescale, the retyped pandas spelling) do not go through a dispatched
kernel at all. This script is what turns that reasoning into a run.
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
    sys.exit(pytest.main(["tests/test_ts_q05_60.py", "-q", "--no-header"]))
