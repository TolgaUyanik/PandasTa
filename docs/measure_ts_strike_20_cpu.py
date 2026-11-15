# -*- coding: utf-8 -*-
"""How much of the unguarded geometric-ladder reading of `ts_strike_20` is
CPU-kernel dependent, and does `tests/test_ts_strike_20.py` survive both?

    python docs/measure_ts_strike_20_cpu.py native            # this machine
    python docs/measure_ts_strike_20_cpu.py disable           # CI's kernels
    python docs/measure_ts_strike_20_cpu.py disable pytest    # + the module

`disable` sets `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
numpy's kernels on a GitHub runner without AVX-512. The variable has to be
set BEFORE numpy is imported, which is why this is a script rather than a
test; `pytest` as a second argument then runs the port's test module in the
same process, under those kernels.

Measured 2026-11-15, the reason the exact unguarded counts came out of
`tests/test_ts_strike_20.py`: the 1%-a-bar ladder reads values 1, 2, 3, 4
with counts 85 / 64 / 80 / 51 native and 87 / 75 / 73 / 45 disabled, while
the x1.5 ladder (1, 2, 3, 5, 8; counts 234 / 25 / 18 / 1 / 2) and the walk's
live range (1 to 9 over 1,480 fired bars) are the same both ways. 144 tests
pass in both configurations.
"""
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "disable":
    os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402
from numpy.lib.stride_tricks import sliding_window_view  # noqa: E402

LENGTH = 20


def unguarded(c, length=LENGTH):
    c = np.asarray(c, dtype=float)
    r = np.full(c.size, np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0
    W = sliding_window_view(r, length)
    mean = W.mean(axis=1)
    flags = W > mean[:, None]
    cur = np.zeros(W.shape[0])
    best = np.zeros(W.shape[0])
    for j in range(length):
        cur = np.where(flags[:, j], cur + 1.0, 0.0)
        best = np.maximum(best, cur)
    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(np.isnan(mean), np.nan, best)
    return out


def walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))


FRAMES = {
    "exp ladder 1%/bar": 100.0 * np.exp(np.arange(300) * 0.01),
    "x1.5 ladder": np.cumprod(np.full(300, 1.5)) * 1e-20,
}

print("NPY_DISABLE_CPU_FEATURES =",
      repr(os.environ.get("NPY_DISABLE_CPU_FEATURES", "")))
for name, frame in FRAMES.items():
    out = unguarded(frame)
    out = out[~np.isnan(out)]
    got, cnt = np.unique(out, return_counts=True)
    print(f"{name}: fired {out.size}, nonzero {int((out > 0).sum())}, "
          f"values {got.astype(int).tolist()}, counts {cnt.tolist()}")

w = unguarded(walk())
w = w[~np.isnan(w)]
print(f"walk(1500): fired {w.size}, min {int(w.min())}, max {int(w.max())}, "
      f"distinct {np.unique(w).astype(int).tolist()}")

if len(sys.argv) > 2 and sys.argv[2] == "pytest":
    import pytest  # noqa: E402
    raise SystemExit(pytest.main(["-q", "tests/test_ts_strike_20.py"]))
