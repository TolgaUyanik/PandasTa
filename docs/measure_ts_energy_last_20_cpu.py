# -*- coding: utf-8 -*-
"""TS-ENERGY-LAST-20: run `tests/test_ts_energy_last_20.py` with numpy's
`AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list
issue-solver re-runs port test modules under, standing in for a GitHub
runner without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift
from what was actually turned off.

    python docs/measure_ts_energy_last_20_cpu.py        # the test module
    python docs/measure_ts_energy_last_20_cpu.py G A1   # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init,
so it has to be in the environment BEFORE numpy is imported -- hence this
file rather than a flag. It sets the variable, imports numpy (asserting
that the dispatch actually took), and runs the module's tests in process.

Why it matters MORE here than for this port's siblings. This module's Gate
A is BIT-equality against the source's own spelling, and both sides of it
are `np.add.reduce` over a contiguous run of `length` float64 -- a
DISPATCHED kernel. The argument for the equality is that the two reduce
the same bytes with the same pairwise blocking, which is a property of the
shape and not of the instruction set, so disabling half the kernels should
move both sides together or neither. That is an argument; this script is
the run that tests it. The same goes for Gate D's x8/x64 bit-identity,
where the division is IEEE-exact whatever the kernel but the two sums are
not.

The frames are built with `np.exp` and `np.cumsum`, which are dispatched
too, so the generated closes themselves can differ in their last bits
between kernels -- which is why every assertion on a distinct-value count
or a ulp distance in `tests/test_ts_energy_last_20.py` is a band and not a
target.

With section names on the command line it runs those sections of
`docs/measure_ts_energy_last_20.py` under the same reduced dispatch
instead of the tests. That is how `docs/TsEnergyLast20Measured.md` §G4
gets its second column of counts: a claim about what a reduced-kernel run
prints has to come from a committed command, not from an environment
variable someone typed once.
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_ts_energy_last_20.py`, imported by path so this works
    whether or not `docs/` is on `sys.path` as a package."""
    path = Path(__file__).resolve().with_name("measure_ts_energy_last_20.py")
    spec = importlib.util.spec_from_file_location("_measure_tsenergy", path)
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
    sys.exit(pytest.main(["tests/test_ts_energy_last_20.py", "-q",
                          "--no-header"]))
