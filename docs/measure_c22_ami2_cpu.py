# -*- coding: utf-8 -*-
"""C22-AMI2: run `tests/test_c22_ami2.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_c22_ami2_cpu.py             # the test module
    python docs/measure_c22_ami2_cpu.py A C D       # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here, and why the answer is unusually clean. Every shipped
value is a function of a 5x5 matrix of INTEGER counts: the mean, the standard
deviation and the window's extremes come out of reductions a vectorised kernel
may reassociate, but they only decide which side of a bin edge each point
falls on, and the measured margin to the nearest edge is 1.25e-06
(`docs/C22Ami2Measured.md` section A11). Below that margin nothing moves at
all -- not in the last bit -- which is why `x10` and `x3.7` come out
bit-identical (section D2). What CAN move in the last bits is the sum of the
25 logarithms, so the tests pin tolerances and bands rather than digits.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_c22_ami2.py`, imported by path so this works whether or
    not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_c22_ami2.py")
    spec = importlib.util.spec_from_file_location("_measure_c22ami2", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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

    want = [a.upper() for a in sys.argv[1:]]
    if want:
        sections = _measure().SECTIONS
        for key in want:
            if key not in sections:
                raise SystemExit(f"unknown section {key!r};"
                                 f" pick from {list(sections)}")
            sections[key]()
        sys.exit(0)
    sys.exit(pytest.main(["tests/test_c22_ami2.py", "-q", "--no-header"]))
