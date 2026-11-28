# -*- coding: utf-8 -*-
"""Does `tests/test_c22_high_fluctuation.py` survive CI's CPU kernels?

    python docs/measure_c22_high_fluctuation_cpu.py native
    python docs/measure_c22_high_fluctuation_cpu.py disable
    python docs/measure_c22_high_fluctuation_cpu.py disable pytest

`disable` sets `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
numpy's kernels on a GitHub runner without AVX-512. The variable has to be
set BEFORE numpy is imported, which is why this is a script rather than a
test; `pytest` as a second argument then runs the port's test module in the
same process, under those kernels.

Unlike `c22_stretch_decreasing` (whose output compares only SIGNS), this
module's mean/std/division DO feed float sums that can move by rounding
across CPU kernels -- but the shipped value is a COUNT over a fixed grid
(`k / (length - 1)`), so a kernel-dependent last-bit move in `Z` only
changes the output if it pushes some `|diff(Z)|` across the 0.04 boundary.
This script reports whether that happened on the test module's own frames,
rather than assuming either way.
"""
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "disable":
    os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402

print("NPY_DISABLE_CPU_FEATURES =",
      repr(os.environ.get("NPY_DISABLE_CPU_FEATURES", "")))
print("numpy cpu features disabled:",
      [k for k, v in np.core._multiarray_umath.__cpu_features__.items()
       if not v])

if len(sys.argv) > 2 and sys.argv[2] == "pytest":
    import pytest  # noqa: E402
    raise SystemExit(pytest.main(["-q", "tests/test_c22_high_fluctuation.py"]))
