# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191098Measured.md for
`pandas_ta.trend.g191_098`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.trend.g191_098 import g191_098

_REAL = importlib.import_module("pandas_ta.trend.g191_098")


def _close(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_098_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _close()
    out = g191_098(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    # Branch counts: both sides of the ternary must actually fire.
    length = 100
    trend_mean = close.rolling(length, min_periods=length).mean()
    gate = ((trend_mean - trend_mean.shift(length)) / close.shift(length)).replace(
        [np.inf, -np.inf], np.nan)
    drawdown_branch = int((gate <= 0.05).sum())
    reversal_branch = int((gate > 0.05).sum())
    gate_nan = int(gate.isna().sum())
    print(f"gate<=0.05 (drawdown branch)={drawdown_branch} "
          f"gate>0.05 (reversal branch)={reversal_branch} gate_nan={gate_nan}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_098(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, length=4, reversal_length=2,
    # threshold=0.05 -- small enough to trace by hand.
    hc = Series([10.0, 11.0, 9.0, 12.0, 20.0, 21.0, 22.0, 30.0, 9.5, 9.0])
    hout = g191_098(hc, length=4, reversal_length=2, threshold=0.05)
    htm = hc.rolling(4, min_periods=4).mean()
    hgate = ((htm - htm.shift(4)) / hc.shift(4)).replace([np.inf, -np.inf], np.nan)
    hdraw = -(hc - hc.rolling(4, min_periods=4).min())
    hrev = -(hc - hc.shift(2))
    hraw = pd.Series(np.where(hgate <= 0.05, hdraw, hrev), index=hc.index)
    hexpected = (hraw / hc).where(hgate.notna())
    print("hand trend_mean:", list(htm))
    print("hand gate:", list(hgate))
    print("hand drawdown:", list(hdraw))
    print("hand reversal:", list(hrev))
    print("hand expected:", list(hexpected))
    print("hand module out:", list(hout))
    pd.testing.assert_series_equal(hout, hexpected, check_names=False)

    # Gate A: spot-check the shipped default against an independent
    # per-bar computation using plain numpy, not pandas' own rolling ops.
    big_c = _close(900, seed=5)
    out_big = g191_098(big_c)
    c = big_c.to_numpy(dtype=float)
    length = 100
    reversal_length = 3
    threshold = 0.05

    def expected_at(t):
        window = c[t - length + 1: t + 1]
        tm_t = window.mean()
        window_prior = c[t - 2 * length + 1: t - length + 1]
        tm_prior = window_prior.mean()
        g = (tm_t - tm_prior) / c[t - length]
        draw = -(c[t] - window.min())
        rev = -(c[t] - c[t - reversal_length])
        raw = draw if g <= threshold else rev
        return raw / c[t]

    for t in (250, 500, 899):
        a, b = out_big.iloc[t], expected_at(t)
        rel = abs(a - b) / abs(b)
        print(f"t={t} module={a!r} independent={b!r} rel_diff={rel:.3e}")
        assert rel < 1e-9

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    close = _close(1500)
    other_c = _close(1500, seed=97)
    offsets = range(250, 1500, 40)

    def leaks(fn):
        base = fn(close)
        hits = 0
        for j in offsets:
            pc = close.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_098)} of {total}")
    shipped = _load_mutant(
        "result = (raw / close).where(gate.notna())",
        "result = (raw / close).where(gate.notna()).shift(-length)",
    )
    print(f"shipped mutant (length-bar write shift) leaks: "
          f"{leaks(shipped.g191_098)} of {total}")
    weaker = _load_mutant(
        "gate = (trend_mean - trend_mean.shift(length)) / close.shift(length)",
        "gate = (trend_mean - trend_mean.shift(length)) / close.shift(-length)",
    )
    print(f"weaker mutant (forward DELAY in gate) leaks: {leaks(weaker.g191_098)} of {total}")


if __name__ == "__main__":
    main()
