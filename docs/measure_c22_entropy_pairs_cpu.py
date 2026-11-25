# -*- coding: utf-8 -*-
"""C22-ENTROPY-PAIRS: run `tests/test_c22_entropy_pairs.py` with numpy's
`AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled -- the list
issue-solver re-runs port test modules under, standing in for a GitHub
runner without AVX-512.

⚠ That is those four features, not "non-AVX kernels": the run prints the
dispatchable features that are STILL enabled, so the claim cannot drift from
what was actually turned off.

    python docs/measure_c22_entropy_pairs_cpu.py             # the test module
    python docs/measure_c22_entropy_pairs_cpu.py A C D       # measured sections

`NPY_DISABLE_CPU_FEATURES` is read by numpy during its CPU-dispatch init, so
it has to be in the environment BEFORE numpy is imported -- hence this file
rather than a flag.

Why the tests do not pin exact digits under this dispatch: the column is a
`bincount` over at most 9 integer categories, feeding `-sum(p * log(p))`. The
integer counts are robust to reassociated reductions (the same reasoning as
`c22_ami2`'s 5x5 table), but the final sum of up to 9 logarithms is not, so
the test module pins `>=` bounds on distinct-value counts and tolerances
(1e-9 to 1e-12) on value comparisons rather than exact counts or `== 0.0`.
"""
import os
import sys
from pathlib import Path

os.environ["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"

import numpy as np  # noqa: E402  (must follow the environment edit)
import pytest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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
        import importlib.util
        path = Path(__file__).resolve().with_name(
            "measure_c22_entropy_pairs.py")
        spec = importlib.util.spec_from_file_location(
            "_measure_c22entropypairs", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for key in want:
            if key not in mod.SECTIONS:
                raise SystemExit(f"unknown section {key!r};"
                                 f" pick from {list(mod.SECTIONS)}")
            mod.SECTIONS[key]()
        sys.exit(0)
    sys.exit(pytest.main(["tests/test_c22_entropy_pairs.py", "-q",
                          "--no-header"]))
