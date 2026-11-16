# -*- coding: utf-8 -*-
"""TF-IQR-RET-60: run `tests/test_tf_iqr_ret_60.py` with numpy's `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list issue-solver
re-runs port test modules under, standing in for a GitHub runner without
AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_tf_iqr_ret_60_cpu.py          # the test module
    python docs/measure_tf_iqr_ret_60_cpu.py A1 D     # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here, and why it matters LESS than it did for
`tf_higuchi_30`. This column is an order-statistic selection: pandas'
`roll_quantile` runs a skiplist in C and the blend is three scalar
operations per quartile, so there is no reduction for a vectorised kernel to
reassociate. What CAN move is upstream of that -- `px / px.shift(1)` is a
dispatched divide, and a last-bit change there can swap two nearly equal
returns and so change WHICH order statistic the column reads. That is why
every overlap figure, every distinct-value count and the level section are
pinned as bands, while the bit-equality claims are kept to places where the
arithmetic is provably the same operation on the same bits: an exact binary
rescale of the price (§D1), where `8a / 8b` IS the double `a / b`; the three
Gate A oracles (§A1-§A3), which read the same returns through the same
blend; and the prototype (§A6), which is the same expression.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_tf_iqr_ret_60.py`, imported by path so this works
    whether or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_tf_iqr_ret_60.py")
    spec = importlib.util.spec_from_file_location("_measure_tfiqrret", path)
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
    sys.exit(pytest.main(["tests/test_tf_iqr_ret_60.py", "-q", "--no-header"]))
