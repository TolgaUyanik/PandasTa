# -*- coding: utf-8 -*-
"""Does `tests/test_msw_lead.py` survive CI's CPU kernels?

    python docs/measure_msw_lead_cpu.py native
    python docs/measure_msw_lead_cpu.py disable
    python docs/measure_msw_lead_cpu.py disable pytest

`disable` sets `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
numpy's kernels on a GitHub runner without AVX-512. The variable has to be
set BEFORE numpy is imported, which is why this is a script rather than a
test; `pytest` as a second argument then runs the port's test module in the
same process, under those kernels.

`msw_lead` feeds rolling dot products and `arctan`/`sin` through a
`np.where` branch whose CONDITION is a float comparison (`|real| > eps`): a
kernel-dependent last-bit move in `real` could, in principle, flip which
branch a bar near the boundary takes. This script reports whether that
happened on the test module's own frames, rather than assuming either way.
"""
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "disable":
    os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402

print("NPY_DISABLE_CPU_FEATURES =",
      repr(os.environ.get("NPY_DISABLE_CPU_FEATURES", "")))
print("numpy cpu features disabled:",
      [k for k, v in np.core._multiarray_umath.__cpu_features__.items()
       if not v])

if len(sys.argv) > 2 and sys.argv[2] == "pytest":
    import pytest  # noqa: E402
    raise SystemExit(pytest.main(["-q", "tests/test_msw_lead.py"]))
