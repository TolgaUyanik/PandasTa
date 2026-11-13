# -*- coding: utf-8 -*-
"""TS-IMQ-20: run `tests/test_ts_imq_20.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_ts_imq_20_cpu.py

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag. It sets the variable, imports numpy (asserting that the
dispatch actually took), and runs the module's tests in process.

Why it matters here: the window total is a numpy reduction and a different
SIMD width changes its last bits. What this column then does with those bits
is a THRESHOLD comparison (`acc / s >= 0.5`), so a last-bit difference does
not shrink -- it either changes nothing at all or moves the reported crossing
by exactly one position, `1 / length` = 0.05. That is why
`tests/test_ts_imq_20.py` pins tolerances of one position and bands of
distinct-value counts rather than exact counts of bit-equal bars, and why the
two-point frame -- where every window sits on that threshold -- has its own
named test instead of being folded into the rescale parametrisation.
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
    sys.exit(pytest.main(["tests/test_ts_imq_20.py", "-q", "--no-header"]))
