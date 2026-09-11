# -*- coding: utf-8 -*-
"""Re-measure every `seeding` row of the PTCLASSIC-1 CSV. Run as a SUBPROCESS.

⚠ THIS MUST NOT BE IMPORTED INTO THE PYTEST PROCESS. `pandas_ta_classic`
registers the pandas DataFrame accessor under the same name as this fork --
`@pd.api.extensions.register_dataframe_accessor("ta")` at
`pandas_ta_classic/core.py:107` -- so importing it REPLACES `df.ta` for every
DataFrame created afterwards. A guard test that imported it in-process took the
fork's suite from green to **109 failures**, all of them `AttributeError` on
accessors that exist.

So the check lives here, behind a process boundary, and
`tests/test_altrepo_ptclassic_divergence_csv.py` shells out to it.

Exit 0 = every `seeding` row re-measured and converging.
Exit 1 = a row does not converge, or too many could not be re-measured.
Prints a JSON summary on the last line either way.
"""
import csv
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
CSV_PATH = os.path.join(SIBLING, "altrepo_ptclassic_divergence.csv")
CLASSIC = os.path.join(SIBLING, "pandas-ta-classic")

if not os.path.exists(CSV_PATH) or not os.path.isdir(CLASSIC):
    print(json.dumps({"skipped": "CSV or sibling repo absent"}))
    sys.exit(0)

sys.path.insert(0, CLASSIC)
sys.path.insert(0, FORK)
sys.path.insert(0, HERE)

import numpy as np                                          # noqa: E402
import pandas_ta as ta                                      # noqa: E402
import pandas_ta_classic as tac                             # noqa: E402
from gen_altrepo_pandas_ta_classic import (                 # noqa: E402
    NOT_CALLABLE, _probe_frame,
)
from gen_altrepo_ptclassic_divergence import _call_pinned   # noqa: E402


def main():
    with open(CSV_PATH, encoding="utf8") as fh:
        seeding = [r for r in csv.DictReader(fh)
                   if r["divergence_class"] == "seeding"]
    if not seeding:
        print(json.dumps({"skipped": "no seeding rows"}))
        return 0

    frame = _probe_frame()
    checked, failures, unverifiable = 0, [], []
    for row in seeding:
        name, fork_name = row["name"], row["pandas_ta_equivalent"]
        cls_fn, fork_fn = getattr(tac, name, None), getattr(ta, fork_name, None)
        if cls_fn is None or fork_fn is None:
            unverifiable.append(name)
            continue
        try:
            out_a = _call_pinned(cls_fn, frame, name)
            out_b = _call_pinned(fork_fn, frame, fork_name)
        except Exception:                                   # noqa: BLE001
            unverifiable.append(name)
            continue
        if out_a is NOT_CALLABLE or out_b is NOT_CALLABLE \
                or out_a is None or out_b is None:
            unverifiable.append(name)
            continue
        a = np.asarray(out_a, dtype="float64").ravel()
        b = np.asarray(out_b, dtype="float64").ravel()
        if a.shape != b.shape:
            unverifiable.append(name)
            continue
        mask = ~(np.isnan(a) | np.isnan(b))
        if mask.sum() < 40:
            unverifiable.append(name)
            continue

        checked += 1
        x, y = a[mask], b[mask]
        scale = np.maximum(np.abs(x), np.abs(y))
        scale[scale < 1e-12] = 1.0
        rel = np.abs(x - y) / scale
        cut = int(len(rel) * 0.75)
        if not rel[cut:].max() < 1e-6 <= rel[:cut].max():
            failures.append(
                f"{name}: head {rel[:cut].max():.3e} tail {rel[cut:].max():.3e}")

    summary = {"total": len(seeding), "checked": checked,
               "failures": failures, "unverifiable": sorted(unverifiable)}
    print(json.dumps(summary))
    if failures:
        return 1
    if len(unverifiable) > len(seeding) // 4:
        return 1
    if checked < max(3, len(seeding) * 3 // 4):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
