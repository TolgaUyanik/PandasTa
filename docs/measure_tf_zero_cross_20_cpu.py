# -*- coding: utf-8 -*-
"""TF-ZERO-CROSS-20: run `tests/test_tf_zero_cross_20.py`, or the measured
sections, with numpy's `AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch
disabled -- the list issue-solver re-runs port test modules under, standing
in for a GitHub runner without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_tf_zero_cross_20_cpu.py          # the test module
    python docs/measure_tf_zero_cross_20_cpu.py A1 D     # measured sections
    python docs/measure_tf_zero_cross_20_cpu.py --all    # every section

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here. This column's own arithmetic is integer -- a sign, a
comparison and two `int64` prefix sums -- so nothing downstream of the
returns can move with the CPU. What CAN move is the input: the synthetic
frames are built with `np.exp` and `np.cumsum`, whose last bits are
dispatched, and a close that moves by one ulp could in principle round to a
different tick or flip the sign of a return that is within an ulp of zero.
That is why the claim "no printed figure moves with the CPU" is made by
comparing the two runs' DIGEST lines, and not from the arithmetic.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_tf_zero_cross_20.py`, imported by path so this works
    whether or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_tf_zero_cross_20.py")
    spec = importlib.util.spec_from_file_location("_measure_tfzc", path)
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

    args = [a.upper() for a in sys.argv[1:]]
    if args:
        measure = _measure()
        want = list(measure.SECTIONS) if args == ["--ALL"] else args
        for key in want:
            if key not in measure.SECTIONS:
                raise SystemExit(f"unknown section {key!r};"
                                 f" pick from {list(measure.SECTIONS)}")
        keys = [k for k in measure.SECTIONS if k in want]
        sha = measure.run(keys)
        print(f"\nDIGEST "
              f"{','.join(k for k in keys if k in measure.DIGESTED)} {sha}")
        sys.exit(0)
    sys.exit(pytest.main(["tests/test_tf_zero_cross_20.py", "-q",
                          "--no-header"]))
