# -*- coding: utf-8 -*-
"""C22-DFA: run `tests/test_c22_dfa.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_c22_dfa_cpu.py             # the test module
    python docs/measure_c22_dfa_cpu.py A C D       # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here, and why the answer is unusually clean. The shipped value
is `break / scales`, a ratio of two small INTEGERS: every float in the
pipeline -- the z-score, the profile, the per-box residuals, the logarithms,
the two straight-line fits -- exists only to decide which of six candidate
breaks minimises one sum. A reassociated reduction has to close a measured
gap of at least 3.6e-04 relative (`docs/C22DfaMeasured.md` section A6) before
any of that can change an output, which is why even an inexact x3.7 price
rescale comes out bit-identical (section D2). What a dispatch change can move
is the sum itself, so the tests pin the integer, the bands and the counts
rather than digits.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_c22_dfa.py`, imported by path so this works whether or
    not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_c22_dfa.py")
    spec = importlib.util.spec_from_file_location("_measure_c22dfa", path)
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
    sys.exit(pytest.main(["tests/test_c22_dfa.py", "-q", "--no-header"]))
