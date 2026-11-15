# -*- coding: utf-8 -*-
"""TF-DFA-100: run `tests/test_tf_dfa_100.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_tf_dfa_100_cpu.py          # the test module
    python docs/measure_tf_dfa_100_cpu.py A1 D     # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here. This column is a least-squares fit on top of a
cumulative sum: `cumsum`, the per-box reductions and the final weighted sum
all run through numpy's dispatched kernels, so every value can move in its
last bits on a different CPU. That is why this port pins bands and orderings
for anything downstream of those reductions, and keeps bit-equality claims to
the three places where the arithmetic is provably the same operation in the
same order: an exact binary rescale of the PRICE (§D), which cannot change a
single input bit; a x-1 rescale of the returns (§L3), where the logarithm
sees the same numbers; and one row of a block against the same row inside the
whole block (§Z2), which is the property the chunk loop rests on.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_tf_dfa_100.py`, imported by path so this works whether
    or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_tf_dfa_100.py")
    spec = importlib.util.spec_from_file_location("_measure_tfdfa", path)
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
    sys.exit(pytest.main(["tests/test_tf_dfa_100.py", "-q", "--no-header"]))
