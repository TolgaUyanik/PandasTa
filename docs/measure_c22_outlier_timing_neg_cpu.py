# -*- coding: utf-8 -*-
"""C22-OUTLIER-TIMING-NEG: re-run this port's own test module and the touched
wiring/doc tests with the CPU-wide SIMD kernels this machine has disabled,
so a result that is only true on an AVX-512 box does not slip through
(`CLAUDE.md`: "Tests must pass on CI's CPUs too"). Sets
`NPY_DISABLE_CPU_FEATURES` before numpy is imported, then hands off to
pytest, mirroring every other port's `measure_*_cpu.py` wrapper.

    python docs/measure_c22_outlier_timing_neg_cpu.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = ["AVX512F", "AVX512_SKX", "AVX2", "FMA3"]


def _detected():
    import numpy as np
    feat = np.core._multiarray_umath.__cpu_features__
    return [f for f in CANDIDATES if feat.get(f)]


def main():
    disable = _detected()
    if not disable:
        print("none of", CANDIDATES, "are present on this CPU; nothing to disable")
        return 0
    env = dict(os.environ)
    env["NPY_DISABLE_CPU_FEATURES"] = " ".join(disable)
    print("NPY_DISABLE_CPU_FEATURES =", env["NPY_DISABLE_CPU_FEATURES"])
    cmd = [sys.executable, "-m", "pytest", "-q",
           "tests/test_c22_outlier_timing_neg.py", "tests/test_readme_counts.py",
           "tests/test_altport2_ports.py", "tests/test_wiring_accessors.py",
           "tests/test_ml_companions.py", "tests/test_gate_e_ledger.py",
           "tests/test_pine_coverage_csv.py",
           "tests/test_prose_counts_match_the_csvs.py"]
    return subprocess.call(cmd, cwd=str(ROOT), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
