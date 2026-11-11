# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191158Measured.md for
`pandas_ta.volatility.g191_158`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.volatility.g191_158 import g191_158

_REAL = importlib.import_module("pandas_ta.volatility.g191_158")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"


def _walk(n=1500, seed=11, sigma=0.015):
    """High/low/close walk with `low <= close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


def _tick_walk(n=1500, seed=23, price=10.0, sigma=0.0025, tick=0.01):
    """The same walk ROUNDED to a tick, so exact OHLC ties exist.

    The continuous-float walk above never produces `high == low` (counted
    below), and a zero-range bar is this column's floor, so the tie case
    needs a frame that can actually reach it. `low <= close <= high` is
    restored after rounding with an explicit min/max."""
    rng = np.random.default_rng(seed)
    close = price * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    close, high, low = (np.round(x / tick) * tick for x in (close, high, low))
    high, low = np.maximum(high, close), np.minimum(low, close)
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


def _opens(high, low, close):
    """A MOVING open for the comparators that read one.

    `pdist` (`2(H-L) - |C-O| + |O-C1|`) and `garman_klass` both read the
    open; a frame with `open == close` would hand them an amputated term,
    so the open is the prior close pulled into the bar's own range."""
    o = close.shift(1)
    o.iloc[0] = close.iloc[0]
    return o.clip(lower=low, upper=high)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_158_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_DIV = "result = (high - low) / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_DIV,
    "result = ((high - low) / close).shift(-1)",
)
FUTURE_RANGE_MUTANT = (
    SHIPPED_DIV,
    # the `bos` look-ahead bug class: tomorrow's range on today's bar
    "result = (high.shift(-1) - low.shift(-1)) / close",
)

OFFSETS = range(50, 1500, 40)  # no warm-up to clear; swept for symmetry with the siblings


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n --
    the operator the source's cancelled term uses, spelled the way
    `pandas_ta/volatility/g191_109.py:101` spells it."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def _literal(high, low, close, n=15, m=2):
    """The source string's LITERAL spelling, before its own reduction:
    `((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C`, with the GTJA `SMA` spelled this
    FORK's way (`min_periods=n`, as `g191_109.py:101` and
    `g191_146.py:106-111` spell it; no fork-wide count is claimed anywhere
    in this port -- see the module docstring for why)."""
    s = _gtja_sma(close, n, m)
    return ((high - s) - (low - s)) / close


def _literal_source_sma(high, low, close, n=15, m=2):
    """The same literal spelling with the GTJA `SMA` spelled the
    PROTOTYPE's way: `x.ewm(alpha=m/n, adjust=False).mean()`, NO
    `min_periods` (`ind_screen.py:57-59`). The 14-bar warm-up of
    `_literal` above is this fork's convention, not the source's, so both
    variants are measured."""
    s = close.ewm(alpha=m / n, adjust=False).mean()
    return ((high - s) - (low - s)) / close


def _prototype(high, low, close):
    """The issue's prototype (`docs/issues/screen/ind_screen.py:517-518`),
    RETYPED, because `docs/issues/` is gitignored and a clone does not carry
    it: `def _(o, h, l, c, v): return (h - l) / c`."""
    return (high - low) / close


def _real_candidate(high, low, close):
    """The REAL `g191_158` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_158"]["fn"](close, high, low, close, ones)


def main():
    print("wiring:")
    print("  g191_158 in Category['volatility']:",
          "g191_158" in ta.Category["volatility"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['volatility'] size:", len(ta.Category["volatility"]))

    high, low, close = _walk()
    out = g191_158(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={int(out.notna().idxmax())}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"negative={int((out.dropna() < 0).sum())} "
          f"zero={int((out.dropna() == 0).sum())}")
    print(f"continuous walk: bars with high == low exactly: "
          f"{int((high == low).sum())} of {n}")

    # Gate C: the tie case. A tick-rounded frame, where a zero-range bar --
    # this column's floor -- is reachable.
    th, tl, tc = _tick_walk()
    tout = g191_158(th, tl, tc)
    ties = int((th == tl).sum())
    print(f"tick-rounded walk ({len(tout)} bars, tick 0.01): high == low on "
          f"{ties} bars; column non-NaN {int(tout.notna().sum())}, "
          f"non-zero {int((tout.dropna() != 0).sum())}, "
          f"zero {int((tout.dropna() == 0).sum())}, "
          f"nunique {int(tout.dropna().nunique())}, "
          f"min={tout.min():.6f} max={tout.max():.6f}")
    print(f"  every zero is a high == low bar: "
          f"{bool(((tout == 0.0) == (th == tl)).all())}")

    # Gate D: price rescale. Volume is not an argument at all, so there is
    # nothing to rescale on that side.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_158(high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        bit_equal = int((out[m] == scaled[m]).sum())
        print(f"x{k} PRICE max|diff|={max_diff!r} "
              f"nan-mask-match={bool((out.isna() == scaled.isna()).all())} "
              f"bit-equal bars={bit_equal} of {fires}")

    # Gate A: hand-derived 6-bar example.
    h6 = Series([10.0, 13.0, 12.0, 16.0, 11.0, 21.0])
    l6 = Series([8.0, 9.0, 8.0, 11.0, 7.0, 15.0])
    c6 = Series([9.0, 12.0, 9.0, 15.0, 8.0, 20.0])
    print("hand-derived 6-bar example:", g191_158(h6, l6, c6).tolist())

    # Gate A: independent per-bar replay, plain Python scalars.
    h9, l9, c9 = _walk(900, seed=5)
    out9 = g191_158(h9, l9, c9)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (h9, l9, c9))
    for t in (0, 300, 600, 899):
        print(f"independent-loop bar {t}: module={out9.iloc[t]!r} "
              f"loop={(hh[t] - ll[t]) / cc[t]!r}")

    # Gate A: the retyped prototype (the SAME expression -- a transcription
    # check, not an independent one) and, when the gitignored screen is
    # present, the REAL candidate out of its own registry.
    proto = _prototype(high, low, close)
    print("port vs retyped prototype: mask-match="
          f"{bool((out.isna() == proto.isna()).all())} "
          f"max|diff|={float((out[m] - proto[m]).abs().max())!r}")
    if SCREEN.exists():
        cand = _real_candidate(high, low, close)
        print("port vs REAL screen candidate: mask-match="
              f"{bool((out.isna() == cand.isna()).all())} "
              f"max|diff|={float((out[m] - cand[m]).abs().max())!r} "
              f"bit-equal bars={int((out[m] == cand[m]).sum())} of {fires}")
    else:
        print("port vs REAL screen candidate: SKIPPED, "
              f"{SCREEN} absent (gitignored)")

    # Gate A, THE decision: the source's own literal spelling, before its own
    # reduction. Costs 14 NaN bars and two roundings.
    lit = _literal(high, low, close)
    both = out.notna() & lit.notna()
    diff = (out[both] - lit[both]).abs()
    rel = diff / out[both].abs()
    print(f"literal spelling ((H-S)-(L-S))/C, S=SMA(C,15,2): "
          f"non-NaN {int(lit.notna().sum())} of {n} (reduced form: {fires}); "
          f"leading NaNs {int(lit.isna().sum())}")
    print(f"  over the {int(both.sum())} bars both define: "
          f"max|diff|={float(diff.max())!r} max|rel diff|={float(rel.max())!r} "
          f"bit-equal bars={int((out[both] == lit[both]).sum())}")
    print(f"  spearman(reduced, literal) over those bars: "
          f"{float(out[both].corr(lit[both], method='spearman'))!r} "
          "(the two are bit-equal here, so anything but 1.0 is the "
          "correlation's own rounding)")

    # ... and the SAME literal spelling with the source's own `sma`, which
    # carries no `min_periods`: there the warm-up disappears entirely, so
    # the 14 NaN bars above are this FORK's convention, not the source's.
    lit_src = _literal_source_sma(high, low, close)
    bs = out.notna() & lit_src.notna()
    print(f"  literal with the PROTOTYPE's own sma (no min_periods): "
          f"non-NaN {int(lit_src.notna().sum())} of {n}, "
          f"over {int(bs.sum())} shared bars "
          f"max|diff|={float((out[bs] - lit_src[bs]).abs().max())!r}, "
          f"bit-equal={int((out[bs] == lit_src[bs]).sum())}")

    # The stated MECHANISM for the bit-equality (Sterbenz: a subtraction of
    # two numbers within a factor of 2 of each other is exact), printed on
    # the frame it is claimed about rather than left as an assertion.
    s_series = _gtja_sma(close, 15, 2)
    ratios = pd.concat([(high / s_series), (s_series / high),
                        (low / s_series), (s_series / low)], axis=1).max(axis=1)
    print(f"  max ratio between H/L and S on this walk: "
          f"{float(ratios[s_series.notna()].max()):.6f} "
          f"(Sterbenz-exact while < 2)")

    # ... and a frame built to BREAK the bit-equality above, so the two
    # spellings are not claimed identical on the strength of one walk: a
    # violent trend, where the smoother S lags far behind the bar, and
    # `H-S` / `L-S` are no longer subtractions of two nearby numbers.
    sh, sl, sc = _walk(1500, seed=4, sigma=0.20)
    s_out, s_lit = g191_158(sh, sl, sc), _literal(sh, sl, sc)
    sb = s_out.notna() & s_lit.notna()
    s_diff = (s_out[sb] - s_lit[sb]).abs()
    s_rel = s_diff / s_out[sb].abs()
    print(f"stress frame (sigma 0.20, S lags the bar): over {int(sb.sum())} "
          f"bars both define, bit-equal={int((s_out[sb] == s_lit[sb]).sum())}, "
          f"differing={int((s_out[sb] != s_lit[sb]).sum())}, "
          f"max|diff|={float(s_diff.max())!r} max|rel diff|={float(s_rel.max())!r}")
    s_series2 = _gtja_sma(sc, 15, 2)
    s_ratios = pd.concat([(sh / s_series2), (s_series2 / sh),
                          (sl / s_series2), (s_series2 / sl)], axis=1).max(axis=1)
    print(f"  max ratio between H/L and S on the stress frame: "
          f"{float(s_ratios[s_series2.notna()].max()):.6f} "
          f"(> 2, which is why bars move here and not on the walk)")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    total = len(list(OFFSETS))
    print(f"real-module leaks: {_leaks(g191_158)} of {total}")
    for label, mut in (("write-shift", WRITE_SHIFT_MUTANT),
                       ("future-range", FUTURE_RANGE_MUTANT)):
        mod = _load_mutant(*mut)
        live = not mod.g191_158(high, low, close).equals(out)
        print(f"{label} mutant: live-differs={live} "
              f"leaks={_leaks(mod.g191_158)} of {total}")

    # The fork column this one is one factor away from: `bw_mfi`'s
    # MFI_BW_SF_20 = ((H-L)/C) / (V/SMA(V,20)). On CONSTANT volume the
    # relative-volume factor is exactly 1.0 and the two columns coincide.
    flat_v = Series(np.full(len(close), 1e6), index=close.index)
    df_flat = pd.DataFrame({"open": close, "high": high, "low": low,
                            "close": close, "volume": flat_v})
    bw_flat = df_flat.ta.bw_mfi()
    mm = out.notna() & bw_flat.notna()
    print(f"bw_mfi on CONSTANT volume: first non-NaN bar "
          f"{int(bw_flat.notna().idxmax())}, overlap {int(mm.sum())} bars, "
          f"max|diff|={float((out[mm] - bw_flat[mm]).abs().max())!r}, "
          f"bit-equal bars={int((out[mm] == bw_flat[mm]).sum())} of {int(mm.sum())}")

    # NaN propagation: one NaN in any input NaNs exactly that bar and no
    # other -- the public docstring's claim, measured.
    for field in ("high", "low", "close"):
        parts = {"high": high.copy(), "low": low.copy(), "close": close.copy()}
        parts[field].iloc[700] = np.nan
        poked = g191_158(**parts)
        moved = [int(i) for i in poked.index[poked.isna() != out.isna()]]
        print(f"NaN in {field} at bar 700: output NaN bars that moved: {moved}, "
              f"every other bar bit-equal: "
              f"{bool((poked.drop(700) == out.drop(700)).all())}")

    # Non-redundancy against the nearest shipped columns, on a 900-bar frame
    # with VARYING volume and a MOVING open (a synthetic stand-in, NOT Gate
    # E -- Gate E is the launcher's run).
    rng = np.random.default_rng(3)
    vol = Series(1e6 * np.exp(rng.normal(0.0, 0.6, len(c9))), index=c9.index)
    o9 = _opens(h9, l9, c9)
    print(f"comparator frame: open == close on {int((o9 == c9).sum())} of "
          f"{len(c9)} bars, open inside [low, high] on "
          f"{int(((o9 >= l9) & (o9 <= h9)).sum())} of {len(c9)}")
    df = pd.DataFrame({"open": o9, "high": h9, "low": l9, "close": c9,
                       "volume": vol})
    own = out9
    others = {
        "bw_mfi:MFI_BW_SF_20": df.ta.bw_mfi(),
        "natr:NATR_14": df.ta.natr(),
        "pdist/close (the Gate E top comparator's shape)": df.ta.pdist() / c9,
        "true_range/close": df.ta.true_range() / c9,
        "g191_109:G191_109_10_2_10_2": df.ta.g191_109(),
        "har_park:HARPARK_1_5_22_500": df.ta.har_park(),
        "massi:MASSI_9_25": df.ta.massi(),
        "cvi:CVI_10_10": df.ta.cvi(),
        "garman_klass:GKVOL_20": df.ta.garman_klass(),
    }
    for name, col in others.items():
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
        mo = own.notna() & col.notna()
        rho = float(own[mo].corr(col[mo], method="spearman"))
        print(f"spearman vs {name}: {rho:.6f} (n={int(mo.sum())})")


if __name__ == "__main__":
    main()
