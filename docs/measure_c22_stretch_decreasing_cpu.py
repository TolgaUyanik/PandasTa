# -*- coding: utf-8 -*-
"""Does `tests/test_c22_stretch_decreasing.py` survive CI's CPU kernels?

    python docs/measure_c22_stretch_decreasing_cpu.py native
    python docs/measure_c22_stretch_decreasing_cpu.py disable
    python docs/measure_c22_stretch_decreasing_cpu.py disable pytest

`disable` sets `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
numpy's kernels on a GitHub runner without AVX-512. The variable has to be
set BEFORE numpy is imported, which is why this is a script rather than a
test; `pytest` as a second argument then runs the port's test module in the
same process, under those kernels.

Unlike `ts_strike_20`'s window MEAN (a float sum that moves by rounding
across kernels), this module's longest-run statistic only compares the SIGN
of a return-to-return diff and compares a window's return span to an
absolute floor via `>`: no float sum or division feeds the output's integer
value, so there is no CPU-kernel-dependent value to report here -- this
script's job is to confirm the test module passes unchanged, not to show a
moved count.
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
    raise SystemExit(pytest.main(["-q", "tests/test_c22_stretch_decreasing.py"]))
