# -*- coding: utf-8 -*-
"""TS-REOCCUR-20: run `tests/test_ts_reoccur_20.py` with numpy's
`AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list
issue-solver re-runs port test modules under, standing in for a GitHub
runner without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift
from what was actually turned off.

    python docs/measure_ts_reoccur_20_cpu.py        # the test module
    python docs/measure_ts_reoccur_20_cpu.py C L    # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init,
so it has to be in the environment BEFORE numpy is imported -- hence this
file rather than a flag. It sets the variable, imports numpy (asserting
that the dispatch actually took), and runs the module's tests in process.

Why it matters here, and the answer is the FRAMES rather than the module.
This column's own arithmetic is one integer division and a pile of float
EQUALITY tests, neither of which a vector kernel can round differently.
What a kernel can move is the frames: they are built with `np.exp`,
`np.cumsum` and `np.round`, so a close can land on a different grid point
in the last bits, and with it every count of distinct values, every
mean and every Spearman in this port's receipt. That is why those are
pinned as bands and orderings in `tests/test_ts_reoccur_20.py`, and why
the exact counts (fired bars, bit-equality, emptied windows) are the ones
pinned to the digit: they are window geometry, not floating point.

With section names on the command line it runs those sections of
`docs/measure_ts_reoccur_20.py` under the same reduced dispatch instead of
the tests -- which is how a claim about what a reduced-kernel run prints
comes from a committed command rather than from an environment variable
someone typed once.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_ts_reoccur_20.py`, imported by path so this works
    whether or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_ts_reoccur_20.py")
    spec = importlib.util.spec_from_file_location("_measure_tsreoccur", path)
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
    sys.exit(pytest.main(["tests/test_ts_reoccur_20.py", "-q",
                          "--no-header"]))
