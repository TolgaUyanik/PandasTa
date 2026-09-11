# -*- coding: utf-8 -*-
"""ALTFIX-2: re-derive every `port` verdict. Run as a SUBPROCESS.

A `port` row asserts the fork does not have the indicator. Nine such assertions
have been wrong. This does not consult a list of names — it runs the sweep and
reports anything the fork reproduces.

⚠ MUST NOT be imported into pytest. `pandas_ta_classic` registers the `df.ta`
accessor under the fork's own name; one in-process import took the suite from
green to 109 failures.

Usage:  python docs/verify_gap_rows.py {pandas-ta-classic|tti|ta-lib}
Prints a JSON summary on the last line. Exit code is always 0; the caller reads
the JSON, so a scan with nothing to check is distinguishable from a failure.
"""
import csv
import importlib.metadata as _md
import io
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
sys.path.insert(0, HERE)
sys.path.insert(0, FORK)

SCAN = sys.argv[1] if len(sys.argv) > 1 else "pandas-ta-classic"


def done(payload):
    print(json.dumps(payload))
    sys.exit(0)


import numpy as np                                          # noqa: E402
import pandas_ta as ta                                      # noqa: E402
from _altrepo_resolve import (                              # noqa: E402
    PINNED_LENGTH, call_fork, fork_surface_cache, probe_variants,
)
from gen_altrepo_pandas_ta_classic import (                 # noqa: E402
    SURFACE, _probe_frame, _same_output,
)

FRAME = _probe_frame()


def fork_cache():
    """The SAME surface the scanners search -- not a subset.

    This built its own cache without `fork_name=`, so it swept 468 variants
    against the scanner's 494 and could not see `ta.stoch(smooth_k=1)`. A guard
    that searches less than the thing it guards cannot catch it.
    """
    return fork_surface_cache(FRAME, SURFACE, ta)


def _round_like(value, decimals):
    if decimals is None or value is None:
        return value
    if isinstance(value, tuple):
        return tuple(_round_like(v, decimals) for v in value)
    return value.round(decimals) if hasattr(value, "round") else value


def reproduced_by(mine, cache, decimals=None):
    """Any fork name whose ANY probed variant reproduces `mine`.

    ⚠ `decimals` rounds BOTH sides. The tti arm rounded only its own side to
    4dp and compared against a full-precision fork cache at rtol=1e-9, so it
    detected 0 of the 13 rows tti's own CSV publishes as `have` -- including
    `TypicalPrice` vs `hlc3`, literally the same number, reported as
    "divergent, max abs diff 5e-05". A detector that has never fired is not a
    detector, which is why `positive_control()` below exists.
    """
    mine = _round_like(mine, decimals)
    for fork_name, values in cache.items():
        for theirs in values:
            outcome, detail = _same_output(mine, _round_like(theirs, decimals),
                                           FRAME)
            if outcome in ("identical", "warmup-offset"):
                return fork_name, detail
    return None, ""


def load_verdict(csv_name, key, verdict):
    path = os.path.join(SIBLING, csv_name)
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf8") as fh:
        return [r[key] for r in csv.DictReader(fh) if r["verdict"] == verdict]


def load(csv_name, key):
    path = os.path.join(SIBLING, csv_name)
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf8") as fh:
        rows = list(csv.DictReader(fh))
    return [r[key] for r in rows if r["verdict"] == "port"]


CSV_FOR_SCAN = KEY_FOR_SCAN = None


def main():
    global CSV_FOR_SCAN, KEY_FOR_SCAN
    cache = fork_cache()

    if SCAN == "pandas-ta-classic":
        names = load("altrepo_pandas_ta_classic.csv", "name")
        CSV_FOR_SCAN, KEY_FOR_SCAN = "altrepo_pandas_ta_classic.csv", "name"
        if names is None:
            done({"skipped": "CSV absent"})
        sys.path.insert(0, os.path.join(SIBLING, "pandas-ta-classic"))
        import pandas_ta_classic as src
        getter = lambda n: getattr(src, n, None)                # noqa: E731
        drive = lambda fn: call_fork(fn, FRAME)                 # noqa: E731

    elif SCAN == "tti":
        names = load("altrepo_tti.csv", "class_name")
        CSV_FOR_SCAN, KEY_FOR_SCAN = "altrepo_tti.csv", "class_name"
        if names is None:
            done({"skipped": "CSV absent"})
        tti_dir = os.path.join(SIBLING, "trading-technical-indicators")
        if not os.path.isdir(tti_dir):
            done({"skipped": "tti checkout absent"})
        _real = _md.version
        _md.version = lambda n: "0.0.0-local" if n == "tti" else _real(n)
        sys.path.insert(0, tti_dir)
        import tti.indicators as src
        getter = lambda n: getattr(src, n, None)                # noqa: E731

        def drive(cls):
            try:
                sub = FRAME[["open", "high", "low", "close", "volume"]].copy()
                out = cls(input_data=sub).getTiData()
                return out.round(4) if hasattr(out, "round") else out
            except Exception:                                   # noqa: BLE001
                return None

    elif SCAN == "ta-lib":
        names = load("altrepo_talib.csv", "name")
        CSV_FOR_SCAN, KEY_FOR_SCAN = "altrepo_talib.csv", "name"
        if names is None:
            done({"skipped": "CSV absent"})
        try:
            from talib import abstract
        except ImportError:
            done({"skipped": "TA-Lib not installed"})
        inputs = {c: FRAME[c].to_numpy(dtype="float64")
                  for c in ("open", "high", "low", "close", "volume")}
        getter = lambda n: n                                    # noqa: E731

        def drive(name):
            from pandas import Series
            try:
                out = abstract.Function(name)(inputs)
            except Exception:                                   # noqa: BLE001
                return None
            if isinstance(out, list):
                out = out[0] if out else None
            if out is None:
                return None
            try:
                return Series(np.asarray(out, dtype="float64"),
                              index=FRAME.index)
            except Exception:                                   # noqa: BLE001
                return None
    else:
        done({"skipped": f"unknown scan {SCAN!r}"})

    # tti rounds every output to 4 decimals; the comparison must happen at that
    # precision on BOTH sides.
    decimals = 4 if SCAN == "tti" else None

    # POSITIVE CONTROL. Before trusting "nothing in the gap is reproducible",
    # prove the detector can detect: re-find the rows the CSV itself calls
    # `have`. The tti arm reported a clean gap while being incapable of finding
    # anything at all.
    detected_have = 0
    have_names = load_verdict(CSV_FOR_SCAN, KEY_FOR_SCAN, "have")[:12]
    for name in have_names:
        obj = getter(name)
        if obj is None:
            continue
        probe = drive(obj)
        if probe is None:
            continue
        if reproduced_by(probe, cache, decimals)[0]:
            detected_have += 1

    reproducible, undrivable, checked = {}, [], 0
    for name in names:
        obj = getter(name)
        if obj is None:
            undrivable.append(name)
            continue
        mine = drive(obj)
        if mine is None:
            undrivable.append(name)
            continue
        checked += 1
        # tti rounds to 4dp; compare the fork side at the same precision.
        probe = mine
        match, detail = reproduced_by(probe, cache, decimals)
        if match:
            reproducible[name] = f"{match}: {detail[:90]}"

    done({"scan": SCAN, "gap_rows": len(names), "checked": checked,
          "undrivable": sorted(undrivable), "reproducible": reproducible,
          "have_probed": len(have_names), "detected_have": detected_have})


if __name__ == "__main__":
    main()
