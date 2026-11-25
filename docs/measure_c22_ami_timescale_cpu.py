# -*- coding: utf-8 -*-
"""C22-AMI-TIMESCALE: run `tests/test_c22_ami_timescale.py` with numpy's
`AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list
issue-solver re-runs port test modules under, standing in for a GitHub runner
without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_c22_ami_timescale_cpu.py          # the test module
    python docs/measure_c22_ami_timescale_cpu.py A D      # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here. Every shipped value is a LAG: an integer decided by
comparing one `rho**2` against its two neighbours. A vectorised kernel that
reassociates the three reductions behind `rho` (`sum(A*B)`, `sum(A*A)`,
`sum(B*B)`) moves those in the last bits, and if two lags were nearly tied
the reported lag would move with them. They are not nearly tied: the measured
minimum gap at the deciding lag is 3.6e-09 (`docs/C22AmiTimescaleMeasured.md`
section D5), seven orders of magnitude above a last-bit question, which is why
the tests pin bounds and bands rather than digits -- and why this run is worth
doing anyway rather than assumed.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_c22_ami_timescale.py`, imported by path so this works
    whether or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_c22_ami_timescale.py")
    spec = importlib.util.spec_from_file_location("_measure_c22ami", path)
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
    sys.exit(pytest.main(["tests/test_c22_ami_timescale.py", "-q",
                          "--no-header"]))
