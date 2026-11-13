# -*- coding: utf-8 -*-
"""TS-MEDSKEW-20: run `tests/test_ts_medskew_20.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled (on this machine `SSSE3`,
`SSE41`, `POPCNT`, `SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`,
`AVX512_CNL`, `AVX512_ICL`), so the claim cannot drift from what was actually
turned off.

    python docs/measure_ts_medskew_20_cpu.py

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag. It sets the variable, imports numpy (asserting that the
dispatch actually took), and runs the module's tests in process.

Why it matters here: the window sum, the squared-deviation sum and the two
extrema are all numpy reductions, and a different SIMD width changes their
last bits. This column divides a DIFFERENCE of two centre readings by a
standard deviation, so those last bits do move the result -- which is why
every cross-check in `tests/test_ts_medskew_20.py` is a tolerance rather than
a bit-equality, except the x8/x64 rescales (the same doubles, so the same
kernels see the same inputs) and the exactly-reproduced NaN masks. This
script is what turns "the tolerances are wide enough" into a run.
"""
import os
import sys

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402

if __name__ == "__main__":
    disabled = np.core._multiarray_umath.__cpu_dispatch__ if hasattr(
        np.core._multiarray_umath, "__cpu_dispatch__") else []
    enabled = [f for f in disabled
               if np.core._multiarray_umath.__cpu_features__.get(f)]
    print(f"numpy {np.__version__}")
    print(f"NPY_DISABLE_CPU_FEATURES = "
          f"{os.environ['NPY_DISABLE_CPU_FEATURES']!r}")
    print(f"dispatchable features still enabled: {enabled}")
    for feature in ("AVX512F", "AVX512_SKX", "AVX2", "FMA3"):
        if feature in enabled:
            raise SystemExit(f"{feature} is still enabled -- the environment "
                             f"edit did not take, so this run proves nothing")
    sys.exit(pytest.main(["tests/test_ts_medskew_20.py", "-q",
                          "--no-header"]))
