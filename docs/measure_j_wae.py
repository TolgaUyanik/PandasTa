# -*- coding: utf-8 -*-
"""J-WAE (PandasTa issue #123): the numbers in `docs/JWaeMeasured.md`,
except the six that receipt names above its §A1 (pytest's own counts, the
before/after counts read off `README.md` and `docs/MLCompanionContract.md`,
issue #123's screen figures, the web-access line, the asserted bounds, and
the reduced-dispatch figures `docs/measure_j_wae_cpu.py` prints).

    python docs/measure_j_wae.py            # every section, in order
    python docs/measure_j_wae.py A1 D1      # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so the RULE is that no
figure may enter the receipt, the module docstring or `tests/test_j_wae.py`
except from a section here or from one of the receipt's named exceptions.

    macd[T] = EMA(close, 20)[T] - EMA(close, 40)[T]     both SMA-seeded
    t1[T]   = (macd[T] - macd[T-1]) * 150
    e1[T]   = BBupper(close, 20, 2)[T] - BBlower(close, 20, 2)[T]
    J_WAE[T] = t1[T] / e1[T]

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here is meant to depend on the machine, and `docs/measure_j_wae_cpu.py`
re-runs the sections under numpy's reduced CPU dispatch to show which
figures move.
"""
import importlib.util
import math
import platform
import sys
import timeit
from pathlib import Path

#: Import THIS checkout's pandas_ta, not whichever one the environment
#: installed: the receipt describes this tree.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from pandas import Series, date_range

import pandas_ta  # noqa: E402
from pandas_ta.momentum.j_wae import (CHANNEL, FAST, MIN_BARS, MULT,
                                      SENSITIVITY, SLOW, j_wae)
from pandas_ta.overlap.ema import ema

N = 1500
LEVEL = 100.0
#: The first bar that can fire on a clean frame, and so the warm-up.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_j_wae.py`, so a number in this
# file and a number in that one are the same measurement. `walk` .. `rising`
# are `docs/measure_j_chandelier_dist.py`'s, kept identical on purpose: two
# ports measured on the same frames can be compared. The high and the low
# are built even though `j_wae` reads only the close, because §L's
# comparators are OHLC indicators.


def _ohlc(close, seed):
    rng = np.random.default_rng(seed + 9_999)
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    """Tick-rounded prices, the shape real BIST bars have."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                 seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    """A constant close: every Bollinger width is exactly 0.0, so the
    `e1 > 0` guard blanks every bar."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _rising(n=N, level=LEVEL, step=0.001):
    """A one-way market: a strictly rising arithmetic ramp, whose MACD
    change settles and whose Bollinger width is constant."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising,
}
#: The six frames whose prices vary in both directions. `flat` and `rising`
#: are degenerate and are reported on their own in §C2.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _close(name):
    return _frame(name)[2]


def _col(name):
    return j_wae(_close(name))


# ----------------------------------------------------------------- oracles


def _oracle(close):
    """The issue's formula, bar by bar, sharing no code with the module.

    Its own SMA seed over `math.fsum`, its own EMA recursion over plain
    Python floats, its own windowed mean and population variance, and the
    LITERAL band subtraction the issue quotes.
    """
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    nan = float("nan")

    def oracle_ema(length):
        out = [nan] * n
        if n < length:
            return out
        alpha = 2.0 / (length + 1.0)
        out[length - 1] = math.fsum(c[:length]) / length
        for i in range(length, n):
            out[i] = (1.0 - alpha) * out[i - 1] + alpha * c[i]
        return out

    fast, slow = oracle_ema(FAST), oracle_ema(SLOW)
    macd = [fast[i] - slow[i] for i in range(n)]
    out = [nan] * n
    for i in range(1, n):
        if i < CHANNEL:
            continue
        window = c[i - CHANNEL + 1:i + 1]
        mean = math.fsum(window) / CHANNEL
        var = math.fsum((x - mean) ** 2 for x in window) / CHANNEL
        dev = MULT * math.sqrt(var)
        e1 = (mean + dev) - (mean - dev)
        t1 = SENSITIVITY * (macd[i] - macd[i - 1])
        if e1 > 0.0 and t1 == t1 and e1 == e1:
            value = t1 / e1
            if math.isfinite(value):
                out[i] = value
    return Series(out, index=close.index)


def _prototype(close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_wae`, retyped
    (that file is gitignored, so it is on the owner's machine only):

        m = ema(c, 20) - ema(c, 40)
        sdiv(150 * m.diff(), 4 * c.rolling(20).std(ddof=0))

    with `ind_screen_r2.py`'s `ema` -- a bare `ewm(span=n, adjust=False)`
    from bar 0, with NO SMA seed -- and the ALGEBRAIC width. ⚠ Not the
    shipped column.
    """
    m = (close.ewm(span=FAST, adjust=False).mean()
         - close.ewm(span=SLOW, adjust=False).mean())
    num = SENSITIVITY * m.diff()
    den = 2.0 * MULT * close.rolling(CHANNEL).std(ddof=0)
    return num / den.where(den > 0.0)


def _alt_adjust_true(close):
    """The same column with pandas' `adjust=True` EMA instead of the
    fork's SMA-seeded `adjust=False`."""
    m = (close.ewm(span=FAST, adjust=True).mean()
         - close.ewm(span=SLOW, adjust=True).mean())
    return _ratio(SENSITIVITY * (m - m.shift(1)), _e1(close))


def _alt_ddof_one(close):
    """The same column with a SAMPLE standard deviation in the width."""
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    sd = np.sqrt(w.var(ddof=1))
    mid, dev = w.mean(), MULT * sd
    return _ratio(_t1(close), (mid + dev) - (mid - dev))


def _alt_algebraic_width(close):
    """The same column with `e1 = 2 * MULT * sd` instead of the literal
    band subtraction the issue quotes."""
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    return _ratio(_t1(close), 2.0 * MULT * np.sqrt(w.var(ddof=0)))


def _t1(close):
    m = ema(close, length=FAST) - ema(close, length=SLOW)
    return SENSITIVITY * (m - m.shift(1))


def _e1(close):
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    mid, dev = w.mean(), MULT * np.sqrt(w.var(ddof=0))
    return (mid + dev) - (mid - dev)


def _ratio(t1, e1):
    out = t1 / e1.where(e1 > 0.0)
    return out.where(np.isfinite(out))


def _talib():
    if importlib.util.find_spec("talib") is None:
        return None
    import talib
    return talib


# --------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _rel(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


def _last_differing_bar(a, b):
    m = a.notna() & b.notna()
    idx = np.flatnonzero(a[m].to_numpy() != b[m].to_numpy())
    if not idx.size:
        return -1
    return int(np.flatnonzero(m.to_numpy())[idx[-1]])


def _first_fire(col):
    nz = np.flatnonzero(col.notna().to_numpy())
    return int(nz[0]) if nz.size else -1


# --------------------------------------------------------------- mutants

SOURCE = (importlib.util.find_spec("pandas_ta.momentum.j_wae").origin)

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar LATER than T.
CAUSALITY_MUTANTS = [
    ("close-lead", "    cl = cl.where(np.isfinite(cl))",
     "    cl = cl.where(np.isfinite(cl)).shift(-1)"),
    ("macd-lead", "    macd = ema(cl, length=FAST) - ema(cl, length=SLOW)",
     "    macd = (ema(cl, length=FAST) - ema(cl, length=SLOW)).shift(-1)"),
    ("t1-lead", "    t1 = SENSITIVITY * (macd - macd.shift(1))",
     "    t1 = SENSITIVITY * (macd.shift(-1) - macd)"),
    ("window-lead", "    window = cl.rolling(CHANNEL, min_periods=CHANNEL)",
     "    window = cl.shift(-1).rolling(CHANNEL, min_periods=CHANNEL)"),
    ("sd-lead", "    sd = np.sqrt(window.var(ddof=0))",
     "    sd = np.sqrt(window.var(ddof=0)).shift(-1)"),
    ("output-early", "    wae = wae.where(np.isfinite(wae))",
     "    wae = wae.where(np.isfinite(wae)).shift(-1)"),
]

#: Edits that are WRONG without reading any later bar. The suffix sweep is
#: blind to all three; Gate A's oracle is not.
BLIND_SPOT_MUTANTS = [
    ("t1-two-bar-change", "    t1 = SENSITIVITY * (macd - macd.shift(1))",
     "    t1 = SENSITIVITY * (macd - macd.shift(2))"),
    ("e1-lagged", "    e1 = (mid + dev) - (mid - dev)",
     "    e1 = ((mid + dev) - (mid - dev)).shift(1)"),
    ("sample-stdev", "    sd = np.sqrt(window.var(ddof=0))",
     "    sd = np.sqrt(window.var(ddof=1))"),
]

#: The three guards, each removable on its own, so each can be priced.
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
E1_GUARD_OFF = ("    wae = t1 / e1.where(e1 > 0.0)", "    wae = t1 / e1")
FINITE_GUARD_OFF = ("    wae = wae.where(np.isfinite(wae))", "    pass")
GUARDS = [("close is finite", CL_GUARD_OFF),
          ("width is positive", E1_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]


def _mutant(*edits):
    """`j_wae` with one or more lines of the SHIPPED source replaced."""
    with open(SOURCE, encoding="utf-8") as fh:
        src = fh.read()
    if len(edits) == 2 and isinstance(edits[0], str):
        edits = [edits]
    for old, new in edits:
        assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
        src = src.replace(old, new)
    ns = {}
    exec(compile(src, "<mutant>", "exec"), ns)
    return ns["j_wae"]


def _caught_at(fn, close, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?"""
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(close).iloc[:j]
    b = fn(close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


def _first_catch_loudness(fn, close, factor=1.03):
    """How far the FIRST caught offset moves a bar before j."""
    for j in OFFSETS:
        f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
                   index=close.index)
        a, b = fn(close).iloc[:j], fn(close * f).iloc[:j]
        if not bool((a.isna() == b.isna()).all()):
            return float("inf")
        m = a.notna() & b.notna()
        if not bool((a[m].to_numpy() == b[m].to_numpy()).all()):
            return float((a[m] - b[m]).abs().max())
    return 0.0


# ---------------------------------------------------------------- printing


def _rule(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def section_env():
    _rule("ENV -- what produced every number below")
    print(f"python {platform.python_version()} on {platform.platform()}")
    print(f"numpy {np.__version__} / pandas {pd.__version__}")
    lib = _talib()
    print(f"talib {lib.__version__ if lib else 'NOT INSTALLED'}")
    print(f"jesse installed: {importlib.util.find_spec('jesse') is not None}")
    here = Path(pandas_ta.__file__).resolve()
    print(f"pandas_ta imported from: "
          f"{here.relative_to(ROOT) if ROOT in here.parents else 'OUTSIDE this checkout'}")
    dispatch = getattr(np.core._multiarray_umath, "__cpu_dispatch__", [])
    enabled = [f for f in dispatch
               if np.core._multiarray_umath.__cpu_features__.get(f)]
    print(f"dispatchable numpy features enabled: {enabled}")
    print(f"constants: SENSITIVITY={SENSITIVITY} FAST={FAST} SLOW={SLOW} "
          f"CHANNEL={CHANNEL} MULT={MULT} MIN_BARS={MIN_BARS}")
    print(f"frames: N={N} LEVEL={LEVEL} warm-up={WARMUP} fired={FIRED}")


def section_A1():
    _rule("A1 -- Gate A: the module vs a bar-by-bar oracle (six frames)")
    print(f"{'frame':<14}{'fired':>7}{'masks':>7}{'bit':>6}"
          f"{'max|abs|':>12}{'max rel':>12}{'spearman':>11}")
    for name in VARYING:
        close = _close(name)
        got, want = j_wae(close), _oracle(close)
        print(f"{name:<14}{int(got.notna().sum()):>7}"
              f"{str(bool((got.isna() == want.isna()).all())):>7}"
              f"{str(_bit_equal(got, want)):>6}"
              f"{_abs(got, want):>12.3e}{_rel(got, want):>12.3e}"
              f"{_spearman(got, want):>11.4f}")
    print(f"first firing bar: "
          f"{sorted({_first_fire(_col(n)) for n in VARYING})}")


def _oracle_legs(close):
    """The oracle's intermediate legs, so §A1b can say WHICH one carries
    the Gate A gap instead of guessing."""
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    nan = float("nan")

    def oracle_ema(length):
        out = [nan] * n
        alpha = 2.0 / (length + 1.0)
        out[length - 1] = math.fsum(c[:length]) / length
        for i in range(length, n):
            out[i] = (1.0 - alpha) * out[i - 1] + alpha * c[i]
        return out

    fast, slow = oracle_ema(FAST), oracle_ema(SLOW)
    macd = [fast[i] - slow[i] for i in range(n)]
    t1 = [nan] + [SENSITIVITY * (macd[i] - macd[i - 1]) for i in range(1, n)]
    e1 = [nan] * n
    for i in range(CHANNEL - 1, n):
        window = c[i - CHANNEL + 1:i + 1]
        mean = math.fsum(window) / CHANNEL
        var = math.fsum((x - mean) ** 2 for x in window) / CHANNEL
        dev = MULT * math.sqrt(var)
        e1[i] = (mean + dev) - (mean - dev)
    idx = close.index
    return {"ema20": Series(fast, index=idx), "ema40": Series(slow, index=idx),
            "macd": Series(macd, index=idx), "t1": Series(t1, index=idx),
            "e1": Series(e1, index=idx)}


def section_A1b():
    _rule("A1b -- WHICH leg carries the Gate A gap")
    print(f"{'frame':<14}{'leg':<8}{'bit-equal':>11}{'max|abs|':>12}"
          f"{'max rel':>12}")
    for name in VARYING:
        close = _close(name)
        want = _oracle_legs(close)
        mine = {"ema20": ema(close, length=FAST), "ema40": ema(close, length=SLOW),
                "macd": ema(close, length=FAST) - ema(close, length=SLOW),
                "t1": _t1(close), "e1": _e1(close)}
        for leg in ("ema20", "ema40", "macd", "t1", "e1"):
            print(f"{name:<14}{leg:<8}"
                  f"{str(_bit_equal(mine[leg], want[leg])):>11}"
                  f"{_abs(mine[leg], want[leg]):>12.3e}"
                  f"{_rel(mine[leg], want[leg]):>12.3e}")
    print("\nand the oracle's seed against the module's, on ALL SIX frames "
          "-- the seed is only half the story, so the recursion's own "
          "residue is printed beside it:")
    print(f"{'frame':<14}{'length':>7}{'seeds equal':>13}"
          f"{'seed |abs|':>12}{'leg bit-equal':>15}{'leg |abs|':>12}")
    for name in VARYING:
        close = _close(name)
        want = _oracle_legs(close)
        for length, leg in ((FAST, "ema20"), (SLOW, "ema40")):
            seed_mine = float(close.iloc[0:length].mean())
            seed_fsum = math.fsum(
                float(x) for x in close.iloc[0:length]) / length
            print(f"{name:<14}{length:>7}"
                  f"{str(seed_mine == seed_fsum):>13}"
                  f"{abs(seed_mine - seed_fsum):>12.3e}"
                  f"{str(_bit_equal(ema(close, length=length), want[leg])):>15}"
                  f"{_abs(ema(close, length=length), want[leg]):>12.3e}")


def section_A2():
    _rule("A2 -- the EMA the module imports: WHERE it seeds, printed")
    print("the module calls `pandas_ta.overlap.ema.ema(close, length)` at "
          "its defaults. This is what that does, measured rather than read "
          "off its signature -- the seeding is the load-bearing reading "
          "(§A4), so it is a cell here and not a sentence.")
    print(f"\n{'frame':<14}{'length':>7}{'first fire':>11}"
          f"{'seed == mean of first n':>25}{'vs bar-0 ewm: differ':>22}")
    for name in VARYING + ["flat", "rising"]:
        close = _close(name)
        for length in (FAST, SLOW):
            leg = ema(close, length=length)
            seed = float(close.iloc[0:length].mean())
            bare = close.ewm(span=length, adjust=False).mean()
            print(f"{name:<14}{length:>7}{_first_fire(leg):>11}"
                  f"{str(float(leg.iloc[length - 1]) == seed):>25}"
                  f"{_differing_bars(leg, bare):>22}")


def section_A3():
    _rule("A3 -- the MACD leg vs this fork's own macd()")
    from pandas_ta.momentum.macd import macd as fork_macd
    print(f"{'frame':<14}{'bit-equal':>11}{'max|abs|':>12}{'fired':>8}")
    for name in VARYING:
        close = _close(name)
        mine = ema(close, length=FAST) - ema(close, length=SLOW)
        theirs = fork_macd(close, fast=FAST, slow=SLOW)[f"MACD_{FAST}_{SLOW}_9"]
        print(f"{name:<14}{str(_bit_equal(mine, theirs)):>11}"
              f"{_abs(mine, theirs):>12.3e}{int(mine.notna().sum()):>8}")


def section_A4():
    _rule("A4 -- WHICH EMA / WHICH stdev: the readings not taken")
    for label, fn in (("screen prototype (no SMA seed, algebraic width)",
                       _prototype),
                      ("pandas adjust=True EMA", _alt_adjust_true),
                      ("sample stdev (ddof=1)", _alt_ddof_one)):
        print(f"\n{label}")
        print(f"{'frame':<14}{'shared':>8}{'differ':>8}{'max|abs|':>12}"
              f"{'last differ':>12}{'spearman':>10}{'their fire':>11}"
              f"{'med |alt|/|this|':>18}")
        for name in VARYING:
            close = _close(name)
            got, alt = j_wae(close), fn(close)
            print(f"{name:<14}"
                  f"{int((got.notna() & alt.notna()).sum()):>8}"
                  f"{_differing_bars(got, alt):>8}"
                  f"{_abs(got, alt):>12.3e}"
                  f"{_last_differing_bar(got, alt):>12}"
                  f"{_spearman(got, alt):>10.4f}"
                  f"{_first_fire(alt):>11}"
                  f"{float((alt.abs() / got.abs()).median()):>18.4f}")


def section_A5():
    _rule("A5 -- TA-Lib as the third speller of the MACD leg")
    lib = _talib()
    if lib is None:
        print("talib is NOT installed; nothing measured here")
        return
    print(f"talib {lib.__version__}")
    print(f"{'frame':<14}{'bit-equal':>11}{'max|abs|':>12}{'max rel':>12}"
          f"{'ta fire':>9}{'our fire':>10}")
    for name in VARYING:
        close = _close(name)
        c = close.to_numpy(dtype=float)
        theirs = Series(lib.EMA(c, FAST) - lib.EMA(c, SLOW), index=close.index)
        mine = ema(close, length=FAST) - ema(close, length=SLOW)
        print(f"{name:<14}{str(_bit_equal(mine, theirs)):>11}"
              f"{_abs(mine, theirs):>12.3e}{_rel(mine, theirs):>12.3e}"
              f"{_first_fire(theirs):>9}{_first_fire(mine):>10}")


def section_A6():
    _rule("A6 -- the width leg vs this fork's bbands, and vs 2*MULT*sd")
    from pandas_ta.volatility.bbands import bbands
    print(f"{'frame':<14}{'bb bit-eq':>11}{'bb max|abs|':>13}"
          f"{'alg bit-eq':>12}{'alg max|abs|':>14}{'alg rel':>11}")
    for name in VARYING:
        close = _close(name)
        mine = _e1(close)
        bb = bbands(close, length=CHANNEL, std=MULT)
        theirs = bb[f"BBU_{CHANNEL}_{MULT}"] - bb[f"BBL_{CHANNEL}_{MULT}"]
        w = close.rolling(CHANNEL, min_periods=CHANNEL)
        alg = 2.0 * MULT * np.sqrt(w.var(ddof=0))
        print(f"{name:<14}{str(_bit_equal(mine, theirs)):>11}"
              f"{_abs(mine, theirs):>13.3e}"
              f"{str(_bit_equal(mine, alg)):>12}"
              f"{_abs(mine, alg):>14.3e}{_rel(mine, alg):>11.3e}")
    print("\nand what that costs the COLUMN (literal vs algebraic width):")
    print(f"{'frame':<14}{'differ':>8}{'of':>8}{'max|abs|':>12}{'max rel':>12}"
          f"{'spearman':>10}")
    for name in VARYING:
        close = _close(name)
        got, alg = j_wae(close), _alt_algebraic_width(close)
        print(f"{name:<14}{_differing_bars(got, alg):>8}"
              f"{int((got.notna() & alg.notna()).sum()):>8}"
              f"{_abs(got, alg):>12.3e}{_rel(got, alg):>12.3e}"
              f"{_spearman(got, alg):>10.4f}")


def section_B1():
    _rule("B1 -- Gate B: the suffix sweep and six look-ahead mutants")
    print(f"the module, over {len(OFFSETS)} offsets {OFFSETS[0]}..{OFFSETS[-1]}")
    for name in VARYING:
        print(f"  {name:<14}caught {_sweep(j_wae, _close(name)):>3}"
              f" of {len(OFFSETS)}")
    print(f"\nmutants, over {SWEPT}")
    print(f"{'mutant':<20}{'walk':>8}{'trend':>8}{'heavy':>8}"
          f"{'first catch |abs|':>20}")
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        caught = [_sweep(fn, _close(n)) for n in SWEPT]
        loud = min(_first_catch_loudness(fn, _close(n)) for n in SWEPT)
        print(f"{label:<20}" + "".join(f"{c:>8}" for c in caught)
              + f"{loud:>20.3e}")


def section_B2():
    _rule("B2 -- Gate B's blind spot: wrong, but not a look-ahead")
    print(f"{'mutant':<20}{'sweep (walk)':>14}{'live?':>8}"
          f"{'vs oracle max|abs|':>20}{'differ':>9}")
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        close = _close("walk")
        got, want = fn(close), _oracle(close)
        print(f"{label:<20}{_sweep(fn, close):>14}"
              f"{str(not _bit_equal(got, j_wae(close))):>8}"
              f"{_abs(got, want):>20.3e}{_differing_bars(got, want):>9}")


def section_C1():
    _rule("C1 -- Gate C: reachability on the six varying frames")
    print(f"{'frame':<14}{'fired':>7}{'of':>6}{'distinct':>10}{'min':>12}"
          f"{'max':>12}{'<0':>7}{'==0':>6}{'|v|<=10':>9}")
    pooled = []
    for name in VARYING:
        col = _col(name)
        v = col.dropna()
        pooled.append(v)
        print(f"{name:<14}{v.size:>7}{N:>6}{v.nunique():>10}"
              f"{v.min():>12.4e}{v.max():>12.4e}"
              f"{int((v < 0).sum()):>7}{int((v == 0).sum()):>6}"
              f"{int((v.abs() <= 10).sum()):>9}")
    all_v = pd.concat(pooled)
    print(f"{'POOLED':<14}{all_v.size:>7}{N * len(VARYING):>6}"
          f"{all_v.nunique():>10}{all_v.min():>12.4e}{all_v.max():>12.4e}"
          f"{int((all_v < 0).sum()):>7}{int((all_v == 0).sum()):>6}"
          f"{int((all_v.abs() <= 10).sum()):>9}")
    print("\nreal-data reachability is OWED: it comes from the launcher's "
          "Gate E run (§E).")


def section_C2():
    _rule("C2 -- the two degenerate frames")
    for name in ("flat", "rising"):
        col = _col(name)
        v = col.dropna()
        print(f"{name:<10}fired {v.size:>5} of {N}  distinct "
              f"{v.nunique() if v.size else 0:>5}  "
              f"min {(v.min() if v.size else float('nan')):.6e}  "
              f"max {(v.max() if v.size else float('nan')):.6e}")
    close = _close("flat")
    print(f"flat: e1 max {float(_e1(close).max()):.3e}, "
          f"t1 max|abs| {float(_t1(close).abs().max()):.3e}")
    close = _close("rising")
    e1, t1 = _e1(close), _t1(close)
    print(f"rising: e1 min {float(e1.min()):.6e} max {float(e1.max()):.6e}, "
          f"t1 min {float(t1.min()):.3e} max {float(t1.max()):.3e}")


def section_D1():
    _rule("D1 -- Gate D: x8 and x64 are bit-identical")
    print(f"{'frame':<14}{'fired':>7}{'x8 bit-eq':>11}{'x64 bit-eq':>12}")
    for name in VARYING:
        close = _close(name)
        base = j_wae(close)
        print(f"{name:<14}{int(base.notna().sum()):>7}"
              f"{str(_bit_equal(base, j_wae(close * 8.0))):>11}"
              f"{str(_bit_equal(base, j_wae(close * 64.0))):>12}")


def section_D2():
    _rule("D2 -- Gate D: inexact rescales, masks, and both error measures")
    print("relative error is printed FOR THE WHOLE COLUMN and again over the "
          "bars where |value| >= 1e-3, because this column crosses zero and a")
    print("relative gap at a bar that reads 1e-13 is a division by the "
          "cancellation, not a scaling failure.")
    print(f"\n{'frame':<14}{'factor':>12}{'max|abs|':>12}{'max rel':>12}"
          f"{'rel |v|>=1e-3':>15}{'masks':>7}")
    worst_abs = worst_rel = worst_big = 0.0
    for name in VARYING:
        close = _close(name)
        base = j_wae(close)
        big = base.abs() >= 1e-3
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            other = j_wae(close * factor)
            masks = bool((base.isna() == other.isna()).all())
            a, r = _abs(base, other), _rel(base, other)
            rb = _rel(base[big], other[big])
            worst_abs, worst_rel = max(worst_abs, a), max(worst_rel, r)
            worst_big = max(worst_big, rb)
            print(f"{name:<14}{factor:>12}{a:>12.3e}{r:>12.3e}"
                  f"{rb:>15.3e}{str(masks):>7}")
    print(f"\nworst of the 24 cells: max|abs| {worst_abs:.3e}, "
          f"max rel {worst_rel:.3e}, max rel over |value| >= 1e-3 "
          f"{worst_big:.3e}")


def section_D3():
    _rule("D3 -- Gate D: the same rescale at three price levels")
    print(f"{'frame':<14}{'level':>10}{'fired':>7}{'x8':>7}{'x64':>7}"
          f"{'largest |t1|':>14}{'largest e1':>13}")
    for name in VARYING[:3]:
        for level in (1e-6, 1e6, 1e100):
            close = _close(name) * (level / LEVEL)
            base = j_wae(close)
            print(f"{name:<14}{level:>10.0e}{int(base.notna().sum()):>7}"
                  f"{str(_bit_equal(base, j_wae(close * 8.0))):>7}"
                  f"{str(_bit_equal(base, j_wae(close * 64.0))):>7}"
                  f"{float(_t1(close).abs().max()):>14.3e}"
                  f"{float(_e1(close).max()):>13.3e}")
    print(f"DBL_MAX = {np.finfo(float).max:.3e}")


def section_D4():
    _rule("D4 -- a level SHIFT moves this column by NOTHING either: it is "
          "AFFINE-invariant, not merely scale-free")
    print("⚠ So the +10 shift that other ports use to show the x8 "
          "bit-identity is not vacuous does NOT work here, and §D5 does the "
          "job instead.")
    print(f"{'frame':<14}{'fired':>7}{'moved by +10':>14}{'max|abs|':>12}"
          f"{'max rel |v|>=1e-3':>19}")
    for name in VARYING:
        close = _close(name)
        base, other = j_wae(close), j_wae(close + 10.0)
        big = base.abs() >= 1e-3
        print(f"{name:<14}{int(base.notna().sum()):>7}"
              f"{_differing_bars(base, other):>14}{_abs(base, other):>12.3e}"
              f"{_rel(base[big], other[big]):>19.3e}")
    print("\nWHY: every EMA of `close + k` is that EMA plus k (the seed is a "
          "mean), so the MACD difference cancels k exactly, and a standard "
          "deviation is shift-invariant. The residue above is the last bits.")


def section_D5():
    _rule("D5 -- the x8/x64 bit-identity is not vacuous: a ONE-BAR nudge is")
    print("a +1% bump at a single bar, which no rescale can imitate.")
    print(f"{'frame':<14}{'bar':>6}{'moved':>8}{'of':>6}{'max|abs|':>12}"
          f"{'first moved':>13}")
    for name in VARYING:
        close = _close(name)
        base = j_wae(close)
        for bar in (700,):
            bumped = close.copy()
            bumped.iloc[bar] = float(bumped.iloc[bar]) * 1.01
            other = j_wae(bumped)
            moved = _differing_bars(base, other)
            m = base.notna() & other.notna()
            idx = np.flatnonzero(base[m].to_numpy() != other[m].to_numpy())
            first = (int(np.flatnonzero(m.to_numpy())[idx[0]])
                     if idx.size else -1)
            print(f"{name:<14}{bar:>6}{moved:>8}"
                  f"{int(base.notna().sum()):>6}{_abs(base, other):>12.3e}"
                  f"{first:>13}")


def section_D6():
    _rule("D6 -- Gate D: 0 < fires < n, and more than one distinct value")
    print(f"{'frame':<14}{'fired':>7}{'of':>6}{'0 < fires < n':>15}"
          f"{'distinct':>10}{'> 1 distinct':>14}")
    for name in VARYING:
        col = _col(name)
        fired = int(col.notna().sum())
        distinct = int(col.dropna().nunique())
        print(f"{name:<14}{fired:>7}{N:>6}{str(0 < fired < N):>15}"
              f"{distinct:>10}{str(distinct > 1):>14}")


def section_G4():
    _rule("G4 -- degenerate and hostile frames raise nothing")
    idx = date_range("2020-01-01", periods=200, freq="h")
    print(f"{'whole frame of':<16}{'bars':>6}{'returned':>10}{'fired':>7}"
          f"{'infinite':>10}{'name':>26}")
    for label, value in (("nan", np.nan), ("+inf", np.inf),
                         ("-inf", -np.inf), ("0.0", 0.0), ("-1.0", -1.0)):
        col = j_wae(Series(np.full(200, value), index=idx))
        print(f"{label:<16}{200:>6}{str(col is not None):>10}"
              f"{int(col.notna().sum()):>7}"
              f"{int(np.isinf(col.to_numpy()).sum()):>10}"
              f"{str(col.name):>26}")
    print("\nand the length boundary:")
    close = _close("walk")
    for n in (MIN_BARS - 1, MIN_BARS, MIN_BARS + 1):
        col = j_wae(close[:n])
        print(f"  {n:>4} bars: "
              f"{'None' if col is None else f'fired {int(col.notna().sum())}'}")


def section_E():
    _rule("E -- Gate E")
    print("PENDING: run by issue-solver after this session, per the task "
          "rules. Nothing in this worktree reads ../Backtesting.")
    print("The screen measured the PROTOTYPE (2026-10-24): max |rho| 0.8698 "
          "vs BB_PctB_Pctl, n = 391,907, top-5 per-frame max median 0.8715, "
          "DISCLOSE_GAP. §A4 measures the prototype as a different column.")


def section_G1():
    _rule("G1 -- guard 1: the close-is-finite guard, priced")
    off = _mutant(*CL_GUARD_OFF)
    close = _close("walk")
    print("one bad close planted at one bar, with the guard and without. "
          "⚠ The bar MATTERS: inside the first SLOW bars it lands in the EMA "
          "SEED, which is a mean, and outside it does not.")
    print(f"{'plant':<10}{'at bar':>7}{'fired on':>9}{'fired off':>10}"
          f"{'masks eq':>9}{'differ':>8}{'max|abs|':>12}{'inf off':>8}")
    for label, value in (("nan", np.nan), ("+inf", np.inf), ("-inf", -np.inf)):
        for bar in (10, 19, 39, 700):
            bad = close.copy()
            bad.iloc[bar] = value
            a, b = j_wae(bad), off(bad)
            print(f"{label:<10}{bar:>7}{int(a.notna().sum()):>9}"
                  f"{int(b.notna().sum()):>10}"
                  f"{str(bool((a.isna() == b.isna()).all())):>9}"
                  f"{_differing_bars(a, b):>8}"
                  f"{_abs(a, b):>12.3e}"
                  f"{int(np.isinf(b.to_numpy()).sum()):>8}")
    print("\nand what the guard costs a CLEAN frame (it must be a no-op):")
    for name in VARYING + ["flat", "rising"]:
        c = _close(name)
        print(f"  {name:<14}bit-equal with the guard off: "
              f"{_bit_equal(j_wae(c), off(c))}")
    print("\nbars a single NaN close removes, with the guard ON:")
    for bar in (10, 700, 1400):
        bad = close.copy()
        bad.iloc[bar] = np.nan
        a = j_wae(bad)
        base = j_wae(close)
        lost = int(base.notna().sum()) - int(a.notna().sum())
        # first bar that differs in mask OR value, so "everything before
        # the plant is unchanged" is a printed index, not a reading
        diff = ((a.isna() != base.isna())
                | (a.notna() & base.notna() & (a != base))).to_numpy()
        first = int(np.flatnonzero(diff)[0]) if diff.any() else -1
        print(f"  plant at {bar:>5}: fired {int(a.notna().sum()):>5} "
              f"(lost {lost:>4}), moved bars "
              f"{_differing_bars(base, a):>5}, "
              f"first differing bar (mask or value) {first:>5}, "
              f"last differing bar {_last_differing_bar(base, a):>5}")

    print("\nWHY a plant at 700 is the SAME with the guard off and a plant "
          "at 10 is not -- the seed and the two pandas behaviours it rests "
          "on, probed directly rather than reasoned about:")
    for bar in (10, 700):
        bad = close.copy()
        bad.iloc[bar] = np.inf
        raw = bad.astype(float)
        guarded = raw.where(np.isfinite(raw))
        for label, series in (("guard ON ", guarded), ("guard OFF", raw)):
            e20 = ema(series, length=FAST)
            macd = e20 - ema(series, length=SLOW)
            print(f"  plant {bar:>4} {label}: seed20="
                  f"{float(series.iloc[0:FAST].mean()):.6e} "
                  f"ema20[{bar}]={float(e20.iloc[bar]):.6e} "
                  f"ema20[19]={float(e20.iloc[19]):.6e} "
                  f"macd notna {int(macd.notna().sum())}")
    probe = Series([1.0, 2.0, np.inf, 4.0, 5.0, 6.0, 7.0])
    print(f"\n  pandas {pd.__version__}, [1, 2, inf, 4, 5, 6, 7]:")
    print(f"    ewm(span=3, adjust=False).mean(): "
          f"{[round(float(v), 4) for v in probe.ewm(span=3, adjust=False).mean()]}"
          f"  <- the inf observation is SKIPPED, exactly like a NaN")
    print(f"    rolling(3).mean():                "
          f"{[round(float(v), 4) for v in probe.rolling(3).mean()]}"
          f"  <- only the windows CONTAINING it are lost; it recovers")
    print(f"    rolling(3).var(ddof=0):           "
          f"{[round(float(v), 4) for v in probe.rolling(3).var(ddof=0)]}")


def _stretch_frame(start=400, stop=601):
    """A `walk` that goes exactly FLAT for a stretch: the Bollinger width
    is 0 once the window is inside it, while the MACD is still catching up,
    so `t1 / e1` is a non-zero over a zero."""
    close = _close("walk").copy()
    close.iloc[start:stop] = float(close.iloc[start])
    return close


def section_G2():
    _rule("G2 -- guards 2 and 3: EACH is a no-op, the PAIR is not")
    one = _mutant(*E1_GUARD_OFF)
    two = _mutant(*FINITE_GUARD_OFF)
    both = _mutant(E1_GUARD_OFF, FINITE_GUARD_OFF)
    print("⚠ Removing `e1 > 0` alone changes nothing because the finite mask "
          "then catches the same bars, and removing the finite mask alone "
          "changes nothing because `e1 > 0` already blanked them. Only "
          "removing BOTH ships an infinity, so they are priced TOGETHER.")
    print(f"\n{'frame':<16}{'fired':>7}{'=w/o e1>0':>11}{'=w/o finite':>13}"
          f"{'fired w/o both':>15}{'inf w/o both':>14}{'zero-width':>12}")
    frames = [(n, _close(n)) for n in VARYING + ["flat", "rising"]]
    frames.append(("flat-stretch", _stretch_frame()))
    for name, close in frames:
        a = j_wae(close)
        b = both(close)
        arr = b.to_numpy()
        print(f"{name:<16}{int(a.notna().sum()):>7}"
              f"{str(_bit_equal(a, one(close))):>11}"
              f"{str(_bit_equal(a, two(close))):>13}"
              f"{int(b.notna().sum()):>15}"
              f"{int(np.isinf(arr).sum()):>14}"
              f"{int((_e1(close) == 0.0).sum()):>12}")
    print("\nthe flat stretch is the case that reaches it: bars 400..600 of "
          "a walk held constant, so the 20-bar width is exactly 0.0 while "
          "the 20/40 EMAs are still converging.")
    close = _stretch_frame()
    e1, t1 = _e1(close), _t1(close)
    zero = e1 == 0.0
    print(f"  zero-width bars {int(zero.sum())}, of which |t1| > 0 on "
          f"{int((t1[zero].abs() > 0).sum())}; largest |t1| there "
          f"{float(t1[zero].abs().max()):.4e}")


def _overflow_frame(kind, n=120):
    """A frame built to overflow the DIVISION on FINITE inputs.

    The ratio is `t1 / e1`, and both legs are homogeneous of degree 1 in
    the price, so a plain rescale cannot reach an infinity: it needs the
    two legs to come from DIFFERENT price regimes. Each of these three
    drops the price by many orders of magnitude at bar 60, so the width is
    computed over the small regime while the 40-bar EMA still carries the
    large one.
    """
    idx = date_range("2020-01-01", periods=n, freq="h")
    rng = np.random.default_rng(5)
    hi, lo = {"tiny-to-subnormal": (1e-10, 1e-320),
              "huge-to-tiny": (1e200, 1e-100),
              "max-to-subnormal": (1e300, 1e-320)}[kind]
    base = np.full(n, lo)
    base[:60] = hi * (1.0 + 0.01 * rng.random(60))
    # the small regime must VARY, or the width is exactly 0.0 and the
    # `e1 > 0` guard -- not this one -- is what blanks the bar.
    base[60:] = lo * (1.0 + np.arange(n - 60) % 3)
    return Series(base, index=idx)


def section_G3():
    _rule("G3 -- the OVERFLOW route the guards do NOT need: not reached")
    off = _mutant(E1_GUARD_OFF, FINITE_GUARD_OFF)
    print("frames built to overflow the DIVISION on finite inputs: a higher "
          "price regime feeding `t1` through the 40-bar EMA while `e1` is "
          "computed over a tiny one.")
    print(f"{'frame':<20}{'bars':>6}{'fired on':>9}{'fired off':>10}"
          f"{'inf off':>9}{'max |t1|':>12}{'min e1>0':>12}")
    for kind in ("tiny-to-subnormal", "huge-to-tiny", "max-to-subnormal"):
        close = _overflow_frame(kind)
        a, b = j_wae(close), off(close)
        arr = b.to_numpy()
        e1 = _e1(close)
        pos = e1[e1 > 0]
        print(f"{kind:<20}{len(close):>6}{int(a.notna().sum()):>9}"
              f"{int(b.notna().sum()):>10}"
              f"{int(np.isinf(arr).sum()):>9}"
              f"{float(_t1(close).abs().max()):>12.3e}"
              f"{(float(pos.min()) if pos.size else float('nan')):>12.3e}")
    print("\nwhere the variance overflows, both readings of the width, bar "
          "by bar after the warm-up (bars CHANNEL-1 ..):")
    print(f"{'frame':<20}{'lit nan&alg inf':>16}{'both inf':>10}"
          f"{'both nan':>10}{'mid inf':>9}{'var inf':>9}{'var nan':>9}"
          f"{'var<0':>7}{'of':>5}{'last nan var':>14}")
    for kind in ("tiny-to-subnormal", "huge-to-tiny", "max-to-subnormal"):
        close = _overflow_frame(kind)
        w = close.rolling(CHANNEL, min_periods=CHANNEL)
        var = w.var(ddof=0).iloc[CHANNEL - 1:]
        mid = w.mean().iloc[CHANNEL - 1:]
        lit = _e1(close).iloc[CHANNEL - 1:]
        alg = (2.0 * MULT * np.sqrt(w.var(ddof=0))).iloc[CHANNEL - 1:]
        nan_bars = np.flatnonzero(var.isna().to_numpy())
        last_nan = int(nan_bars[-1]) + CHANNEL - 1 if nan_bars.size else -1
        print(f"{kind:<20}"
              f"{int((lit.isna() & np.isinf(alg)).sum()):>16}"
              f"{int((np.isinf(lit) & np.isinf(alg)).sum()):>10}"
              f"{int((lit.isna() & alg.isna()).sum()):>10}"
              f"{int(np.isinf(mid).sum()):>9}"
              f"{int(np.isinf(var).sum()):>9}"
              f"{int(var.isna().sum()):>9}"
              f"{int((var < 0).sum()):>7}"
              f"{len(var):>5}{last_nan:>14}")
    print("inf variance bars, by index:")
    for kind in ("tiny-to-subnormal", "huge-to-tiny", "max-to-subnormal"):
        close = _overflow_frame(kind)
        var = close.rolling(CHANNEL, min_periods=CHANNEL).var(ddof=0)
        print(f"  {kind:<20}{list(np.flatnonzero(np.isinf(var.to_numpy())))}"
              f"  var NaN on bars CHANNEL.. : "
              f"{int(var.iloc[CHANNEL:].isna().sum())} of "
              f"{len(var.iloc[CHANNEL:])}")
    print("\nthe RuntimeWarnings this probe raises, counted rather than "
          "described (pandas' rolling variance goes marginally negative on "
          "a subnormal window, and `sqrt` of that is a NaN the guards then "
          "blank):")
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for kind in ("tiny-to-subnormal", "huge-to-tiny", "max-to-subnormal"):
            j_wae(_overflow_frame(kind))
    print(f"  {len(caught)} warning(s) over the three frames: "
          f"{sorted({str(w.message) for w in caught})}")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for name in VARYING + ["flat", "rising"]:
            j_wae(_close(name))
    print(f"  {len(caught)} warning(s) over the eight ordinary frames")

    print("\nand with BOTH output guards off the ordinary frames are "
          "unchanged, so the overflow route is not reached there either:")
    for name in VARYING + ["flat", "rising"]:
        c = _close(name)
        print(f"  {name:<14}bit-equal with both guards off: "
              f"{_bit_equal(j_wae(c), off(c))}")


def section_L():
    _rule("L -- in-fork overlap, SYNTHETIC: a disclosure, not Gate E")
    from pandas_ta.momentum.macd import macd
    from pandas_ta.momentum.pgo import pgo
    from pandas_ta.momentum.squeeze import squeeze
    from pandas_ta.momentum.roc import roc
    from pandas_ta.volatility.atr import atr
    from pandas_ta.volatility.bbands import bbands

    def _comparators(high, low, close):
        hist = macd(close)["MACDh_12_26_9"]
        bb = bbands(close, length=CHANNEL, std=MULT)
        width = bb[f"BBU_{CHANNEL}_{MULT}"] - bb[f"BBL_{CHANNEL}_{MULT}"]
        pctb = (close - bb[f"BBL_{CHANNEL}_{MULT}"]) / width.where(width > 0)
        out = {
            "MACD_Hist_ATR (retyped, invented)":
                hist / atr(high, low, close, length=14),
            "MACDh_12_26_9 / close": hist / close,
            "pgo:PGO_14": pgo(high, low, close, length=14),
            "squeeze:SQZ_20_2.0_20_1.5":
                squeeze(high, low, close)["SQZ_20_2.0_20_1.5"],
            "bbands %B (20, 2)": pctb,
            "roc:ROC_10": roc(close, length=10),
            "1-bar change of %B": pctb.diff(),
        }
        return out

    rows = {}
    for name in VARYING:
        high, low, close = _frame(name)
        col = j_wae(close)
        for label, other in _comparators(high, low, close).items():
            rows.setdefault(label, []).append(abs(_spearman(col, other)))
    print(f"{'comparator':<36}{'median |rho|':>13}{'max':>9}{'min':>9}")
    for label, vals in sorted(rows.items(),
                              key=lambda kv: -np.nanmedian(kv[1])):
        print(f"{label:<36}{np.nanmedian(vals):>13.4f}"
              f"{np.nanmax(vals):>9.4f}{np.nanmin(vals):>9.4f}")
    print("\n⚠ six SYNTHETIC frames, not the 89 real ones Gate E uses. The "
          "screen's own fork-overlap stage put pgo:PGO_14 nearest at 0.8562 "
          "on 12 REAL frames.")


def section_Z():
    _rule("Z -- cost (THIS machine, THIS run; nothing else cites these)")
    close = _close("walk")
    for label, fn in (("j_wae", lambda: j_wae(close)),
                      ("the oracle", lambda: _oracle(close))):
        best = min(timeit.repeat(fn, number=10, repeat=3)) / 10 * 1e3
        print(f"{label:<14}{best:>9.3f} ms per call on {N} bars")


SECTIONS = {
    "ENV": section_env, "A1": section_A1, "A1B": section_A1b,
    "A2": section_A2, "A3": section_A3,
    "A4": section_A4, "A5": section_A5, "A6": section_A6, "B1": section_B1,
    "B2": section_B2, "C1": section_C1, "C2": section_C2, "D1": section_D1,
    "D2": section_D2, "D3": section_D3, "D4": section_D4, "D5": section_D5,
    "D6": section_D6, "E": section_E,
    "G1": section_G1, "G2": section_G2, "G3": section_G3, "G4": section_G4,
    "L": section_L, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
        SECTIONS[key]()
