# -*- coding: utf-8 -*-
"""J-GATOR: run `tests/test_j_gator.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

    python docs/measure_j_gator_cpu.py          # the test module
    python docs/measure_j_gator_cpu.py A1 D     # measured sections

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift
from what was actually turned off.

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init,
so it has to be in the environment BEFORE numpy is imported -- hence this
file rather than a flag.

Why it matters here, and the answer is BOTH the frames and the column.
The frames are built with `np.exp` and `np.cumsum`, so a reduced kernel
can move a price in its last bits. And the column is a difference of two
nearby EWMAs, which amplifies a last-bit move by orders of magnitude
(§D(b): an inexact rescale of the PRICE by 1e-16 shows up as 6.5e-10 in
the column). That is why `tests/test_j_gator.py` pins bounds, shapes and
implications, and keeps bit-equality only where the operations are
identical by construction: the prototype comparison and the x8/x64
rescale.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_j_gator.py`, imported by path so this works whether or
    not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_j_gator.py")
    spec = importlib.util.spec_from_file_location("_measure_jgator", path)
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
    sys.exit(pytest.main(["tests/test_j_gator.py", "-q", "--no-header"]))
