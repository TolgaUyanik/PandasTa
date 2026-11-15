# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191022Measured.md for
`pandas_ta.momentum.g191_022`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_022 import g191_022

_REAL = importlib.import_module("pandas_ta.momentum.g191_022")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"

BIAS_LENGTH, DELAY_LENGTH, SMOOTH_LENGTH, SMOOTH_WEIGHT = 6, 3, 12, 1


def _walk(n=1500, seed=11, sigma=0.015):
    """Close-only lognormal walk; this column reads nothing but `close`."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


def _ohlcv(close, seed=3):
    """An OHLCV frame around a close walk, for the comparator accessors."""
    rng = np.random.default_rng(seed)
    sigma = 0.0075
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma, len(close))))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma, len(close))))
    open_ = close.shift(1)
    open_.iloc[0] = close.iloc[0]
    open_ = open_.clip(lower=low, upper=high)
    vol = Series(1e6 * np.exp(rng.normal(0.0, 0.6, len(close))), index=close.index)
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": vol})


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_022_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_MEAN = "mean6 = close.rolling(bias_length).mean()"
SHIPPED_CHANGE = "change = bias - bias.shift(delay_length)"
SHIPPED_RESULT = "result = _gtja_sma(change, smooth_length, smooth_weight)"

WRITE_SHIFT_MUTANT = (
    SHIPPED_RESULT,
    "result = _gtja_sma(change, smooth_length, smooth_weight).shift(-smooth_length)",
)
CENTERED_MEAN_MUTANT = (
    SHIPPED_MEAN,
    # the `bos` look-ahead bug class
    "mean6 = close.rolling(bias_length, center=True).mean()",
)
FORWARD_DELAY_MUTANT = (
    SHIPPED_CHANGE,
    # DELAY read forward: this formula's own most plausible sign slip
    "change = bias - bias.shift(-delay_length)",
)

OFFSETS = range(50, 1500, 40)  # past the 19-bar warm-up


def _leaks(fn):
    close = _walk(1500)
    other = _walk(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        poked = close.copy()
        poked.iloc[j:] = other.iloc[j:].values
        out = fn(poked)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def _prototype(close):
    """The issue's prototype (`docs/issues/screen/ind_screen.py:317-321`),
    RETYPED, because `docs/issues/` is gitignored and a clone does not carry
    it:

        b = (c - mean(c, 6)) / mean(c, 6)
        return sma(b - delay(b, 3), 12, 1)

    with `mean`/`delay`/`sma` as `ind_screen.py:45,47,57-59` define them --
    and note the prototype's `sma` carries NO `min_periods`, so this is the
    SOURCE spelling of the smoother, not the fork's."""
    b = (close - close.rolling(6).mean()) / close.rolling(6).mean()
    return (b - b.shift(3)).ewm(alpha=1 / 12, adjust=False).mean()


def _prototype_fork_sma(close):
    """The same prototype expression with the fork's `min_periods=n` on the
    GTJA `SMA` -- what the shipped module computes, spelled independently."""
    b = (close - close.rolling(6).mean()) / close.rolling(6).mean()
    return (b - b.shift(3)).ewm(alpha=1 / 12, adjust=False, min_periods=12).mean()


def _real_candidate(close):
    """The REAL `g191_022` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_022"]["fn"](close, close, close, close, ones)


def _independent_loop(close, t):
    """`G191_022[t]` from plain Python scalars: no `.rolling()`, no
    `.shift()`, no `.ewm()`. The GTJA recursion is seeded exactly the way
    `adjust=False` seeds it -- Y at the first valid input IS that input --
    and then run forward bar by bar."""
    c = close.to_numpy(dtype=float)
    first_bias = BIAS_LENGTH - 1
    first_change = first_bias + DELAY_LENGTH

    def bias_at(i):
        mean = sum(c[i - BIAS_LENGTH + 1:i + 1]) / BIAS_LENGTH
        return (c[i] - mean) / mean

    y = None
    alpha = SMOOTH_WEIGHT / SMOOTH_LENGTH
    for i in range(first_change, t + 1):
        change = bias_at(i) - bias_at(i - DELAY_LENGTH)
        y = change if y is None else alpha * change + (1.0 - alpha) * y
    return y


def main():
    print("wiring:")
    print("  g191_022 in Category['momentum']:",
          "g191_022" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    close = _walk()
    out = g191_022(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    m = out.notna()
    print(f"\nname={out.name} n={n} fires={fires} ({100 * fires / n:.2f}%) "
          f"nunique={nunique} first_valid_index={int(out.notna().idxmax())}")
    print(f"min={out.min():.8f} max={out.max():.8f} median={out.median():.8f} "
          f"positive={int((out.dropna() > 0).sum())} "
          f"negative={int((out.dropna() < 0).sum())} "
          f"zero={int((out.dropna() == 0).sum())}")

    # Gate A: hand-derived small example at tiny parameters, printed so the
    # doc's arithmetic can be checked against the module.
    small = Series([10.0, 11.0, 12.0, 11.0, 13.0, 14.0, 13.0, 15.0])
    hand = g191_022(small, bias_length=2, delay_length=1, smooth_length=2,
                    smooth_weight=1)
    print("\nhand-derived 8-bar example (bias_length=2, delay_length=1, "
          f"smooth_length=2, smooth_weight=1): {[float(x) for x in hand]}")
    print(f"  name={hand.name}")

    # Gate A: independent per-bar replay, plain Python scalars.
    nine = _walk(900, seed=5)
    out9 = g191_022(nine)
    for t in (19, 300, 600, 899):
        print(f"independent-loop bar {t}: module={out9.iloc[t]!r} "
              f"loop={_independent_loop(nine, t)!r}")

    # Gate A: the retyped prototype, in both spellings of the GTJA SMA.
    proto_fork = _prototype_fork_sma(close)
    print("\nport vs retyped prototype (fork SMA, min_periods=12): mask-match="
          f"{bool((out.isna() == proto_fork.isna()).all())} "
          f"max|diff|={float((out[m] - proto_fork[m]).abs().max())!r} "
          f"bit-equal bars={int((out[m] == proto_fork[m]).sum())} of {fires}")
    proto = _prototype(close)
    shared = out.notna() & proto.notna()
    print("port vs retyped prototype (SOURCE SMA, no min_periods): "
          f"non-NaN {int(proto.notna().sum())} of {n} (port: {fires}); "
          f"over {int(shared.sum())} shared bars "
          f"max|diff|={float((out[shared] - proto[shared]).abs().max())!r} "
          f"bit-equal bars={int((out[shared] == proto[shared]).sum())}")
    print(f"  the port's extra leading NaNs: "
          f"{int(out.isna().sum())} vs {int(proto.isna().sum())}")

    if SCREEN.exists():
        cand = _real_candidate(close)
        cm = out.notna() & cand.notna()
        print("port vs REAL screen candidate: candidate non-NaN "
              f"{int(cand.notna().sum())} of {n}; over {int(cm.sum())} shared "
              f"bars max|diff|={float((out[cm] - cand[cm]).abs().max())!r} "
              f"bit-equal bars={int((out[cm] == cand[cm]).sum())}")
        rt = _prototype(close)
        rm = rt.notna() & cand.notna()
        print("retyped prototype vs REAL screen candidate: over "
              f"{int(rm.sum())} shared bars "
              f"max|diff|={float((rt[rm] - cand[rm]).abs().max())!r} "
              f"bit-equal bars={int((rt[rm] == cand[rm]).sum())} of {int(rm.sum())}")
    else:
        print(f"port vs REAL screen candidate: SKIPPED, {SCREEN} absent")

    # Gate A: the reading of `DELAY(that,3)`. The rejected reading differs,
    # measured rather than dismissed.
    bias = (close - close.rolling(6).mean()) / close.rolling(6).mean()
    shipped_change = bias - bias.shift(3)
    other_reading = bias - shipped_change.shift(3)  # `that` = the subtraction
    alt = other_reading.ewm(alpha=1 / 12, adjust=False, min_periods=12).mean()
    am = out.notna() & alt.notna()
    print(f"\nthe rejected reading of `DELAY(that,3)` (`that` = the whole "
          f"subtraction): over {int(am.sum())} shared bars "
          f"max|diff|={float((out[am] - alt[am]).abs().max())!r} "
          f"bit-equal bars={int((out[am] == alt[am]).sum())} "
          f"spearman={float(out[am].corr(alt[am], method='spearman')):.6f}")

    # The shipped `bias` is the same inner term in the other spelling.
    df = _ohlcv(close)
    shipped_bias = df.ta.bias(length=BIAS_LENGTH)
    bm = bias.notna() & shipped_bias.notna()
    print(f"\ninner term vs shipped bias(length=6) `(close/SMA)-1`: name="
          f"{shipped_bias.name} over {int(bm.sum())} bars "
          f"max|diff|={float((bias[bm] - shipped_bias[bm]).abs().max())!r} "
          f"bit-equal bars={int((bias[bm] == shipped_bias[bm]).sum())} "
          f"max|rel diff|="
          f"{float(((bias[bm] - shipped_bias[bm]).abs() / bias[bm].abs()).max())!r}")
    via_bias = (shipped_bias - shipped_bias.shift(3)).ewm(
        alpha=1 / 12, adjust=False, min_periods=12).mean()
    vm = out.notna() & via_bias.notna()
    print(f"  the whole column rebuilt on top of shipped bias: over "
          f"{int(vm.sum())} bars max|diff|="
          f"{float((out[vm] - via_bias[vm]).abs().max())!r} "
          f"bit-equal bars={int((out[vm] == via_bias[vm]).sum())} of {int(vm.sum())} "
          f"spearman={float(out[vm].corr(via_bias[vm], method='spearman')):.8f}")

    # Gate D: price rescale. `close` is the only input.
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_022(close * k)
        sign_changed = int((np.sign(out[m]) != np.sign(scaled[m])).sum())
        print(f"x{k} PRICE max|diff|={float((out[m] - scaled[m]).abs().max())!r} "
              f"nan-mask-match={bool((out.isna() == scaled.isna()).all())} "
              f"bit-equal bars={int((out[m] == scaled[m]).sum())} of {fires} "
              f"sign-changed bars={sign_changed}")

    # Gate B: future-perturbation leak counts, real module vs. three mutants.
    total = len(list(OFFSETS))
    print(f"\nreal-module leaks: {_leaks(g191_022)} of {total}")
    for label, mut in (("write-shift", WRITE_SHIFT_MUTANT),
                       ("centered-mean", CENTERED_MEAN_MUTANT),
                       ("forward-delay", FORWARD_DELAY_MUTANT)):
        mod = _load_mutant(*mut)
        live = not mod.g191_022(close).equals(out)
        print(f"{label} mutant: live-differs={live} "
              f"leaks={_leaks(mod.g191_022)} of {total}")

    # Warm-up boundary, measured at the exact lengths the module enforces.
    min_length = BIAS_LENGTH + DELAY_LENGTH + SMOOTH_LENGTH - 1
    print(f"\nmin_length={min_length}; on {min_length - 1} bars the module "
          f"returns {g191_022(_walk(min_length - 1))}")
    exact = g191_022(_walk(min_length))
    print(f"on exactly {min_length} bars: non-NaN {int(exact.notna().sum())}, "
          f"first valid index {int(exact.notna().idxmax())}, "
          f"last value {float(exact.iloc[-1])!r}")

    # NaN propagation: measured, because the `ewm` does NOT empty its output
    # on a NaN input -- it carries the previous value forward.
    poked = close.copy()
    poked.iloc[700] = np.nan
    pout = g191_022(poked)
    moved_nan = [int(i) for i in pout.index[pout.isna() != out.isna()]]
    differing = int((pout.dropna() != out.reindex(pout.dropna().index)).sum())
    first_diff = pout.index[(pout != out) & pout.notna() & out.notna()]
    print(f"\nNaN in close at bar 700: output bars whose NaN-ness moved: "
          f"{moved_nan}; non-NaN bars whose value moved: {differing}; "
          f"first moved bar: {int(first_diff[0]) if len(first_diff) else None}; "
          f"last moved bar: {int(first_diff[-1]) if len(first_diff) else None}")

    # Non-redundancy on a synthetic frame -- NOT Gate E (the launcher's run).
    own = out
    others = {
        "bias:BIAS_SMA_6 (the inner term itself)": df.ta.bias(length=6),
        "bias:BIAS_SMA_26 (the shipped default)": df.ta.bias(),
        "the UNSMOOTHED change (bias - bias.shift(3))": shipped_change,
        "roc:ROC_10": df.ta.roc(),
        "cmo:CMO_14": df.ta.cmo(),
        "rsi:RSI_14": df.ta.rsi(),
        "slope:SLOPE_1": df.ta.slope(),
        "g191_002:G191_002_1": df.ta.g191_002(),
        "g191_129:G191_129_12": df.ta.g191_129(),
        "g191_167:G191_167_12": df.ta.g191_167(),
        "ppo:PPO_12_26_9": df.ta.ppo(),
        # The issue's Gate E top comparator for the PROTOTYPE was
        # `smi_SMIo_5_20_5`, the OSCILLATOR line -- selected by name here,
        # because `df.ta.smi()` returns three columns and a positional
        # `iloc[:, 0]` would quietly measure `SMI_5_20_5` instead.
        "smi:SMIo_5_20_5 (the issue's Gate E top comparator)":
            df.ta.smi()["SMIo_5_20_5"],
        "smi:SMI_5_20_5 (the same indicator's first line)": df.ta.smi(),
    }
    print()
    for label, col in others.items():
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
        mo = own.notna() & col.notna()
        rho = float(own[mo].corr(col[mo], method="spearman"))
        print(f"spearman vs {label}: {rho:.6f} (n={int(mo.sum())})")


if __name__ == "__main__":
    main()
