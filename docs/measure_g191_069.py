# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191069Measured.md for
`pandas_ta.trend.g191_069`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.trend.g191_069 import g191_069

_REAL = importlib.import_module("pandas_ta.trend.g191_069")


def _ohlc(n=1500, seed=23, lo=50.0, hi=150.0):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1.5, n)
    close = lo + np.abs(np.cumsum(steps)) % (hi - lo)
    close = Series(close)
    open_ = close.shift(1).fillna(close.iloc[0]) + rng.normal(0, 0.5, n)
    gap_up = rng.uniform(0, 1.0, n)
    gap_dn = rng.uniform(0, 1.0, n)
    high = pd.concat([open_, close], axis=1).max(axis=1) + gap_up
    low = pd.concat([open_, close], axis=1).min(axis=1) - gap_dn
    return open_, high, low, close


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_069_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    open_, high, low, close = _ohlc()
    out = g191_069(open_, high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_069(open_ * k, high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 7-bar example at length=3 (includes a flat-open
    # boundary bar, open == open1).
    hand_open = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0])
    hand_high = Series([102.0, 108.0, 106.0, 104.0, 110.0, 100.0, 115.0])
    hand_low = Series([98.0, 102.0, 100.0, 101.0, 104.0, 92.0, 107.0])
    hand_out = g191_069(hand_open, hand_high, hand_low, hand_open, length=3)
    print("hand-derived bars 0..6:", list(hand_out.iloc[0:7]))

    # Independent per-bar replay using plain numpy array slicing, not
    # pandas' own .rolling()/np.where calls, spot-checking the shipped
    # defaults (length=20).
    big_open, big_high, big_low, big_close = _ohlc(900, seed=5)
    out_defaults = g191_069(big_open, big_high, big_low, big_close)
    o = big_open.to_numpy(dtype=float)
    h = big_high.to_numpy(dtype=float)
    l = big_low.to_numpy(dtype=float)
    length = 20

    def dtm_dbm_at(i):
        o1 = o[i - 1]
        dtm = 0.0 if o[i] <= o1 else max(h[i] - o[i], o[i] - o1)
        dbm = 0.0 if o[i] >= o1 else max(o[i] - l[i], o[i] - o1)
        return dtm, dbm

    for t in (300, 600, 899):
        sd, sb = 0.0, 0.0
        for i in range(t - length + 1, t + 1):
            dtm, dbm = dtm_dbm_at(i)
            sd += dtm
            sb += dbm
        if sd > sb:
            expected = (sd - sb) / sd
        elif sd < sb:
            expected = (sd - sb) / sb
        else:
            expected = 0.0
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={expected!r}")

    # Gate B: future-perturbation leak counts, real module vs. one mutant.
    o2, h2, l2, c2 = _ohlc(seed=41)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(open_, high, low, close)
        hits = 0
        for j in offsets:
            po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
            po.iloc[j:] = o2.iloc[j:].values
            ph.iloc[j:] = h2.iloc[j:].values
            pl.iloc[j:] = l2.iloc[j:].values
            pc.iloc[j:] = c2.iloc[j:].values
            out_p = fn(po, ph, pl, pc)
            a, b = base.iloc[:j], out_p.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_069)} of {total}")
    write_shift = _load_mutant(
        "    ).where(sd.notna() & sb.notna())",
        "    ).where(sd.notna() & sb.notna()).shift(-length)",
    )
    print(f"write-shift mutant (length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_069)} of {total}")


def _ml_form_counts():
    import os
    import re
    from collections import Counter
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = open(os.path.join(here, "docs", "IndicatorDictionary.md"), encoding="utf8").read()
    body = doc[doc.index("## candles"):]
    tags = Counter(re.findall(r"`[^`]+`\s+(PX2|PX|SF|BIN|ORD|CONST|\?\?)(?!\w)", body))
    print("ML form counts:", dict(tags), "total:", sum(tags.values()))


def _wiring_counts():
    import pandas as pd
    import pandas_ta as ta
    cat = ta.Category
    total = sum(len(v) for v in cat.values())
    accessor_count = sum(
        1 for n in dir(pd.DataFrame().ta.__class__)
        if not n.startswith("_") and callable(getattr(pd.DataFrame().ta.__class__, n))
    )
    print(f"Category total={total} trend_bucket={len(cat['trend'])} accessor_count={accessor_count}")


if __name__ == "__main__":
    main()
    _wiring_counts()
    _ml_form_counts()
