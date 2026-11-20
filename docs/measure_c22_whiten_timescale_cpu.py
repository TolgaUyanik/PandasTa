# -*- coding: utf-8 -*-
"""C22-WHITEN-TIMESCALE: run `tests/test_c22_whiten_timescale.py`, or
sections of `docs/measure_c22_whiten_timescale.py`, with numpy's `AVX2` and
`FMA3` dispatch disabled -- the setting the port's CPU check re-runs test
modules under.

⚠ That is those two features and nothing more: the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_c22_whiten_timescale_cpu.py          # the test module
    python docs/measure_c22_whiten_timescale_cpu.py A X      # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why it matters here. Every value is decided by the SIGN of a lagged sum. On
the five stochastic frames the smallest deciding |sum| / sum of squares is
1.66e-05 (`docs/C22WhitenTimescaleMeasured.md` section D3), far above a
last-bit question. On the exact cosine frame it is 6.78e-18, so a float
spelling's rounding can decide it -- and under this dispatch the FFT
reference does, on one window (section A1 here, section X for the module
against the exact oracle on every cosine window).
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402


def _measure():
    """`docs/measure_c22_whiten_timescale.py`, imported by path."""
    path = Path(__file__).resolve().with_name("measure_c22_whiten_timescale.py")
    spec = importlib.util.spec_from_file_location("_measure_c22whiten", path)
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
    for feature in ("AVX2", "FMA3"):
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
    sys.exit(pytest.main(["tests/test_c22_whiten_timescale.py", "-q",
                          "--no-header", "-p", "no:cacheprovider"]))
