# -*- coding: utf-8 -*-
"""ALTPORT-2: the three ALTPORT-1 survivors, ported.

`cvi` (pandas-ta-classic, MIT), `bw_mfi` (the question tti's
`MarketFacilitationIndex` asks, MIT) and `smc_sweep` (pandas-ta-classic, MIT).
Six of the nine ALTPORT-1 candidates did NOT arrive here -- `C_POSC_14` was
struck at Gate E, three were skipped on question-redundancy and two on an
owner ruling -- and `docs/AltportPortsMeasured.md` keeps them in its table with
their measurements.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate B, and specifically that the J SWEEP is load-bearing for
   `smc_sweep`.** Prefix truncation cannot see back-dating, so causality is
   tested by future-perturbation: perturb every bar from J onward, assert
   nothing before J moves. Measured over **775 J values** (J = 20..794) on an
   800-bar frame:

       cvi        real leaks at   0/775 J   back-dating mutant caught at 775/775
       bw_mfi     real leaks at   0/775 J   back-dating mutant caught at 775/775
       smc_sweep  real leaks at   0/775 J   back-dating mutant caught at  87/775

   **87 of 775 is 11.2%.** A test that had picked ONE J would have missed the
   `smc_sweep` mutant nine times out of ten -- and it misses it at J = 100,
   150, 200, 250, 500, 600 and 700, four of which are the round numbers a test
   author reaches for. The reason is structural, not incidental: the output is
   a +/-1 flag that fires on ~1.6% of bars (measured: 7,152 of 422,136 real
   BIST daily bars), so a one-bar back-date only surfaces when a bar adjacent
   to J happens to be an event. This is the CANDLE-1 escape, reproduced.

   ⚠ A SECOND, more obvious `smc_sweep` mutant is deliberately NOT used and is
   recorded here because it looks like a test and is not one: back-dating the
   SWING LOOKUP (`.shift(1)` -> `.shift(-1)`) makes `low < swing_low`
   arithmetically impossible -- the rolling window then contains the bar it is
   compared against -- so the mutant emits a CONSTANT ZERO, 0 events against
   the real module's 90, and no perturbation of any input can move a constant.
   It scores 0 leak at all 775 J and would have been read as "causal".
   `test_the_degenerate_smc_mutant_is_degenerate` pins that so nobody
   "strengthens" the test back into blindness.

2. **Gate A -- agreement with the UPSTREAM package, in a SUBPROCESS.**
   `pandas_ta_classic` registers a `df.ta` accessor under the same name as this
   fork, and importing it in-process inside the suite took the run to 109
   failures. Every Gate A check here runs in a child interpreter. Measured by
   `docs/gen_altport2_ports.py` over ALTPORT-0's 12 named BIST daily frames:

       cvi        vs pandas_ta_classic.cvi        max|diff| 0.0        n 51,794
       smc_sweep  vs pandas_ta_classic.smc_sweep  max|diff| 0.0        n 52,022
       bw_mfi raw vs (high-low)/volume            max|diff| 0.0        n 50,722
       bw_mfi raw vs tti MarketFacilitationIndex  max|diff| 4.99967e-11 n 50,722

   The 4.99967e-11 is tti's `.round(10)` half-ulp floor, not a disagreement --
   it is the largest agreement a rounded reference permits. **The seeding
   divergence ALTPORT-1 warned to expect did NOT occur for `cvi`**, and that is
   a measurement, not an assumption: classic's `ema` and this fork's `ema` BOTH
   seed with an SMA at bar `length`, and they differ only in how they locate
   the first valid bar (classic uses `first_valid_index`, the fork position 0),
   which cannot differ on a `high - low` series with no leading NaN. The
   warm-up window is diffed on its own (`n = 72`, max|diff| 0.0) so a head-only
   divergence cannot hide inside a pooled maximum.

3. **Gate D -- bit-identical, `== 0.0`, not a tolerance.** ALTPORT-1 measured
   `C_MFI_BW_SF_20` FAILING Gate D at x8 (0.004193). That was tti's rounding,
   and it does not transfer: re-run on the fork implementation, all three
   columns are bit-identical at O/H/L/C x8 and x64 on AEFES_IS (5,545-5,695
   comparable bars each), NaN masks matching. `MFI_BW_SF_20` is additionally
   bit-identical under VOLUME x8 -- the relative-volume ratio cancels -- which
   is a property `natr`-style width columns do not have and is the reason this
   column is shipped as a double ratio instead of `(high-low)/volume`.

4. **Gate E is RE-MEASURED for `bw_mfi`, not inherited, and the re-measurement
   moved it.** ALTPORT-1 screened `C_MFI_BW_SF_20` as tti's ROUNDED `mfi` with
   volume multiplied back out. The shipped column does not round, and the
   difference is not cosmetic: pooled over the same 89 frames,
   Spearman(shipped, screened) is **0.927845** and max|shipped - screened| is
   **1.41628e+07** -- the `.round(10)` quantum on `(h-l)/volume` amplified by
   BIST volumes that reach 1e10. So Gate E was re-run on the shipped column
   against the same 496 comparators:

       column            pooled max |rho|  against            n        verdict
       CVI_10_10                 0.501290  CHOP               405,514  SHIP
       MFI_BW_SF_20              0.578897  vol_at_low_ratio   394,399  SHIP
       SMC_SWEEP_15_1.5          0.161383  CCI                406,562  SHIP

   `CVI_10_10` and `SMC_SWEEP_15_1.5` reproduce ALTPORT-1's figures TO THE
   DIGIT because they are bit-identical to the screened series (max|d| 0.0,
   rho 1.000000 pooled over 408,253 bars) -- the carry-over is a result here,
   not an argument. `MFI_BW_SF_20` rose 0.536816 -> **0.578897**, which is
   close to ALTPORT-1's own unrounded prediction of 0.573380 and still far
   under the 0.76 ship line. Harness:
   `../Backtesting/scripts/analysis/measure_altport2_gate_e.py`.

5. **`smc_sweep` stays SIGNED.** An unsigned magnitude nonzero only on its own
   event's support correlates rho ~ 1.0000 with any other such column -- the
   tied-zero trap that killed six CANDLE-1 columns. Measured on the real cache:
   2,547 `+1` and 4,605 `-1` of 422,136 bars. If someone "simplifies" this to
   an unsigned flag, `test_smc_sweep_is_signed_on_real_data` fails.

6. **Gate C -- every shipped column fires on real data, counted.** 578
   `*_1d.parquet` files in `../Backtesting/datastore/cache/`, 92 of them usable
   (OHLCV present, >= 800 bars), 422,136 pooled bars:

       CVI_10_10         non-NaN 420,388   non-zero 420,388   92/92 frames fire
       MFI_BW_SF_20      non-NaN 402,610   non-zero 401,798   91/92 frames fire
       SMC_SWEEP_15_1.5  non-NaN 422,136   non-zero   7,152   92/92 frames fire

   ⚠ `MFI_BW_SF_20` fires on **91 of 92**, not 92. The one frame is not a
   defect and is not hidden: it has fewer than `length` bars of nonzero volume
   in the usable window, so the relative-volume denominator never settles. The
   test asserts >= 90, so a real regression cannot hide behind that allowance.

7. **The wiring, all five touch points.** 221 -> **224** in `Category`
   (trend 55 -> 56, volatility 18 -> 19, volume 21 -> 22), one accessor each,
   and every one callable from a bulk `df.ta.strategy()` sweep -- none of the
   three needs an argument a sweep cannot supply, so none belongs in
   `strategy`'s exclusion list beside `vp`.

8. **Attribution, and that neither upstream repo is committed here.** Both
   sources are MIT, which is permissive but still requires attribution; each
   module names its upstream repository in its header.

NOT pinned here: the Gate E sweep itself, which needs the parent engine's
492-column production output and cannot run in a unit test. It lives in
`../Backtesting/scripts/analysis/measure_altport2_gate_e.py` and its CSVs, and
the verdicts are tabulated in `docs/AltportPortsMeasured.md`.
"""
import glob
import importlib.util
import os
import subprocess
import sys

import numpy as np
import pytest
from pandas import DataFrame, date_range, read_parquet

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.trend import smc_sweep
from pandas_ta.volatility import cvi
from pandas_ta.volume import bw_mfi

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_FORK)
CACHE = os.path.join(_ROOT, "Backtesting", "datastore", "cache")
CLASSIC = os.path.join(_ROOT, "AlternativeRepos", "pandas-ta-classic")
TTI = os.path.join(_ROOT, "AlternativeRepos", "trading-technical-indicators")

SHIPPED_COLUMNS = ["CVI_10_10", "MFI_BW_SF_20", "SMC_SWEEP_15_1.5"]

REGISTERED = {
    "volatility": ["cvi"],
    "volume": ["bw_mfi"],
    "trend": ["smc_sweep"],
}

#: `Category` totals AFTER this port. 221 before; the three buckets each +1.
#: Moved 224 -> 231 by PINEBI-1b tranche 1 (kcw, rwi, pzo, vzo, szo, rms, wpo).
#: The number is pinned, not computed, precisely so an accidental Category
#: edit fails here instead of silently shipping.
CATEGORY_TOTAL = 231
CATEGORY_BUCKETS = {"trend": 56, "volatility": 20, "volume": 23}

#: Gate E, re-measured on the SHIPPED columns over 89 BIST_100 daily frames /
#: 408,253 bars against 496 comparators. See docstring item 4.
GATE_E = {
    "CVI_10_10": (0.501290, "CHOP", 405514),
    "MFI_BW_SF_20": (0.578897, "vol_at_low_ratio", 394399),
    "SMC_SWEEP_15_1.5": (0.161383, "CCI", 406562),
}

#: What ALTPORT-1 screened, and did not survive to here. Kept so the file
#: records the deletions rather than only the ships.
NOT_PORTED = {
    "C_POSC_14": "STRUCK at Gate E: pooled 0.894742 vs cfo, per-frame median "
                 "0.910212, >= 0.90 on 62.9% of 89 frames",
    "C_HVOL_20": "question-redundancy skip: 0.834724 vs natr, and natr IS "
                 "'how volatile is this stock'",
    "C_PB_WIDTH_PCT": "question-redundancy skip: 0.874411 vs natr",
    "C_WAD_BAR_SF": "question-redundancy skip: 0.889416 vs percent_return",
    "C_PB_UP_DIST_PCT": "owner ruling NO on the slope correction being a new "
                        "question (0.773573 vs dist_from_high_5)",
    "C_PB_LO_DIST_PCT": "owner ruling NO, together with its mirror "
                        "(0.727354 vs cfo)",
}


# ----------------------------------------------------------------- frames

def _frame(n=800, seed=7):
    """An event-rich synthetic frame.

    Small bodies and fat wicks on purpose: at the default seed a plain
    random-walk frame produces ZERO `smc_sweep` events, and a Gate B mutant
    test on a constant-zero column proves nothing.
    """
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    open_ = close + rng.normal(0, 0.25, n)
    high = np.maximum(open_, close) + abs(rng.normal(0, 2.5, n))
    low = np.minimum(open_, close) - abs(rng.normal(0, 2.5, n))
    idx = date_range("2022-01-01", periods=n, freq="D")
    return DataFrame({"open": open_, "high": high, "low": low, "close": close,
                      "volume": rng.integers(1e5, 1e6, n).astype(float)},
                     index=idx)


def _columns(d):
    return {
        "CVI_10_10": ta.cvi(d["high"], d["low"]),
        "MFI_BW_SF_20": ta.bw_mfi(d["high"], d["low"], d["close"], d["volume"]),
        "SMC_SWEEP_15_1.5": ta.smc_sweep(d["open"], d["high"], d["low"], d["close"]),
    }


def _real_frames(limit=None):
    files = sorted(glob.glob(os.path.join(CACHE, "*_1d.parquet")))
    out = []
    for p in files:
        d = read_parquet(p)
        d.columns = [str(c).lower() for c in d.columns]
        if not {"open", "high", "low", "close", "volume"}.issubset(d.columns):
            continue
        d = d[["open", "high", "low", "close", "volume"]].dropna()
        if len(d) < 800:
            continue
        out.append((os.path.basename(p)[:-11], d))
        if limit and len(out) >= limit:
            break
    return len(files), out


_needs_cache = pytest.mark.skipif(
    not os.path.isdir(CACHE) or not glob.glob(os.path.join(CACHE, "*_1d.parquet")),
    reason="parent repo's parquet cache is absent")
_needs_classic = pytest.mark.skipif(
    not os.path.isdir(CLASSIC), reason="../AlternativeRepos/pandas-ta-classic absent")


# ------------------------------------------------------------- names/API

def test_the_three_columns_are_named_what_the_docs_say():
    """Naming is API: mined rules in the parent repo match on these strings."""
    d = _frame()
    for name, s in _columns(d).items():
        assert s.name == name, f"{s.name!r} != {name!r}"


def test_bw_mfi_does_not_collide_with_the_money_flow_index():
    """`mfi` is the Money Flow Index and was here first."""
    d = _frame()
    assert ta.mfi(d["high"], d["low"], d["close"], d["volume"]).name.startswith("MFI_")
    assert ta.bw_mfi(d["high"], d["low"], d["close"], d["volume"]).name == "MFI_BW_SF_20"
    assert "bw_mfi" not in ta.Category["volume"][:0]      # placeholder-safe
    assert "mfi" in ta.Category["volume"] and "bw_mfi" in ta.Category["volume"]


def test_cvi_splits_the_ema_period_from_the_roc_lookback():
    """Upstream exposes ONE `length` for both; the port defaults to that."""
    d = _frame()
    assert ta.cvi(d["high"], d["low"], length=10).name == "CVI_10_10"
    assert ta.cvi(d["high"], d["low"], length=10, roc_length=4).name == "CVI_10_4"
    a = ta.cvi(d["high"], d["low"], length=10)
    b = ta.cvi(d["high"], d["low"], length=10, roc_length=10)
    assert (a - b).abs().max() == 0.0


def test_bw_mfi_raw_is_reachable_but_registered_nowhere():
    """Bill Williams' index is a PRICE PER SHARE -- an oracle, not a feature."""
    d = _frame()
    raw = ta.bw_mfi(d["high"], d["low"], d["close"], d["volume"], raw=True)
    assert raw.name == "MFI_BW_RAW_20"
    expected = (d["high"] - d["low"]) / d["volume"]
    assert (raw - expected).abs().max() == 0.0
    for names in ta.Category.values():
        assert "bw_mfi_raw" not in names


# --------------------------------------------------------------- wiring

def test_all_five_wiring_touch_points():
    for category, names in REGISTERED.items():
        for name in names:
            spec = importlib.util.find_spec(f"pandas_ta.{category}.{name}")
            assert spec is not None, f"1: no module pandas_ta/{category}/{name}.py"
            pkg = importlib.import_module(f"pandas_ta.{category}")
            assert callable(getattr(pkg, name, None)), \
                f"2: {name} not exported from pandas_ta.{category}"
            assert name in ta.Category[category], \
                f"3: {name} not in Category[{category!r}]"
            assert callable(getattr(DataFrame().ta, name, None)), \
                f"4: no df.ta.{name}() accessor"
    # 5 is this file.


def test_the_category_count_moved_by_exactly_three():
    """A missing trailing comma silently CONCATENATES two adjacent strings and
    deletes two indicators. The total and the per-bucket counts are both
    asserted so a compensating pair of errors cannot cancel."""
    total = sum(len(v) for v in ta.Category.values())
    assert total == CATEGORY_TOTAL, f"Category total {total}, expected {CATEGORY_TOTAL}"
    for bucket, n in CATEGORY_BUCKETS.items():
        assert len(ta.Category[bucket]) == n, \
            f"Category[{bucket!r}] has {len(ta.Category[bucket])}, expected {n}"
    for names in ta.Category.values():
        for n in names:
            assert " " not in n, f"concatenated Category entry: {n!r}"


def test_none_of_the_three_needs_a_strategy_exclusion():
    """Anything needing an argument a bulk sweep cannot supply belongs beside
    `vp` in the exclusion list. These three take OHLCV only, so they must NOT
    be excluded -- and the sweep is actually run to prove it."""
    d = _frame(n=300)
    out = d.copy()
    out.ta.cvi(append=True)
    out.ta.bw_mfi(append=True)
    out.ta.smc_sweep(append=True)
    for name in SHIPPED_COLUMNS:
        assert name in out.columns, f"{name} did not append"


# ------------------------------------------- Gate A (SUBPROCESS ONLY)

_GATE_A = r"""
import sys, warnings
warnings.filterwarnings("ignore")
import importlib.metadata as _md
_rv = _md.version
_md.version = lambda n: ("0.0.0-local" if n == "tti" else _rv(n))
sys.path.insert(0, %r)      # classic
sys.path.insert(0, %r)      # fork  (LAST insert wins the df.ta accessor; we
                            #        never touch df.ta here either way)
import numpy as np, pandas as pd
import pandas_ta as ta
import pandas_ta_classic as tac

rng = np.random.default_rng(7)
n = 800
c = 100 + np.cumsum(rng.normal(0, 1.0, n))
o = c + rng.normal(0, 0.25, n)
h = np.maximum(o, c) + abs(rng.normal(0, 2.5, n))
l = np.minimum(o, c) - abs(rng.normal(0, 2.5, n))
idx = pd.date_range("2022-01-01", periods=n, freq="D")
o, h, l, c = (pd.Series(x, index=idx) for x in (o, h, l, c))
v = pd.Series(rng.integers(1e5, 1e6, n).astype(float), index=idx)

def d(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    fa, fb = np.isfinite(a), np.isfinite(b)
    assert (fa == fb).all(), "NaN masks differ"
    m = fa & fb
    assert m.sum() > 700, m.sum()
    return float(np.abs(a[m] - b[m]).max())

print("CVI", d(ta.cvi(h, l, length=10), tac.cvi(h, l, length=10)))
print("SMC", d(ta.smc_sweep(o, h, l, c), tac.smc_sweep(o, h, l, c)))
print("BW", d(ta.bw_mfi(h, l, c, v, raw=True), (h - l) / v))
assert "pandas_ta_classic" in sys.modules
print("OK")
"""


@_needs_classic
def test_gate_a_against_pandas_ta_classic_in_a_subprocess():
    """`pandas_ta_classic` registers `df.ta` under the SAME name as this fork.

    Importing it in-process inside the suite took the run to 109 failures, so
    Gate A runs in a child interpreter -- always, even though nothing here
    touches `df.ta`. The pinned numbers are 0.0 on both classic ports: this
    fork's `ema` and classic's `ema` both SMA-seed at bar `length`, so the
    seeding divergence that separated `dx` upstream does not arise for `cvi`.
    """
    proc = subprocess.run([sys.executable, "-c", _GATE_A % (CLASSIC, _FORK)],
                          capture_output=True, text=True, cwd=_FORK)
    assert proc.returncode == 0 and "OK" in proc.stdout, \
        f"Gate A subprocess failed:\n{proc.stdout}\n{proc.stderr}"
    got = dict(line.split() for line in proc.stdout.strip().splitlines()
               if line != "OK")
    assert float(got["CVI"]) == 0.0, f"cvi vs classic: {got['CVI']}"
    assert float(got["SMC"]) == 0.0, f"smc_sweep vs classic: {got['SMC']}"
    assert float(got["BW"]) == 0.0, f"bw_mfi raw vs (h-l)/v: {got['BW']}"


def test_no_test_module_imports_pandas_ta_classic_in_process():
    """The whole class, scanned -- not just this file.

    `docs/gen_altport0_triage.py` and `docs/gen_altport2_ports.py` DO import it
    and say so in their docstrings; they are not tests and are excluded by
    living outside `tests/`.
    """
    # Parse, do not grep. A raw text scan cannot tell a real import from the
    # same words inside a SUBPROCESS SCRIPT TEMPLATE -- this module embeds one,
    # and the first version of this guard reported its own subprocess text as an
    # offender. A guard with a false positive gets switched off, so it walks the
    # AST and only real module- or function-level imports count.
    import ast as _ast

    offenders = []
    for p in glob.glob(os.path.join(_HERE, "*.py")):
        src = open(p, encoding="utf8").read()
        try:
            tree = _ast.parse(src)
        except SyntaxError:                                 # pragma: no cover
            continue
        for node in _ast.walk(tree):
            names = []
            if isinstance(node, _ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, _ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                if name.split(".")[0] == "pandas_ta_classic":
                    offenders.append(
                        f"{os.path.basename(p)}:{node.lineno}: imports {name}")
    assert offenders == [], (
        "a test imports pandas_ta_classic in-process; it registers the `df.ta` "
        "accessor under the same name as this fork and took the suite to 109 "
        f"failures. Use a subprocess.\n{offenders}")


# ------------------------------------------------- Gate B (mutants + J sweep)

_J_SWEEP = range(20, 795)


def _mutate(module, old, new):
    """Read the shipped module's source, apply one edit, exec it in memory."""
    spec = importlib.util.find_spec(module)
    src = open(spec.origin, encoding="utf8").read()
    # `old`/`new` may be a single string or a tuple of them. A mutant that has
    # to patch TWO sites is not a convenience: `smc_sweep` reads a swing low AND
    # a swing high, and patching one leaves the other branch live, producing a
    # HALF-degenerate mutant that still looks like it detects something.
    olds = (old,) if isinstance(old, str) else tuple(old)
    news = (new,) if isinstance(new, str) else tuple(new)
    assert len(olds) == len(news)
    mutated = src
    for o, n in zip(olds, news):
        before = mutated
        mutated = mutated.replace(o, n)
        assert mutated != before, (
            f"the mutation did not apply to {module} -- blind test: {o!r}")
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)
    return ns[module.rsplit(".", 1)[1]]


def _perturb(d, J):
    """Replace the FUTURE, from bar J onward, with a materially different one.

    A uniform additive shift is not enough for `smc_sweep`: adding a constant
    to every price leaves a rolling MIN of lows unchanged whenever the pre-J
    lows are already the lower ones. Highs are stretched up and lows down so
    both extremes are guaranteed to move.
    """
    e = d.copy()
    m = np.arange(len(d)) >= J
    e.loc[m, "high"] *= 1.7
    e.loc[m, "low"] *= 0.5
    e.loc[m, "close"] *= 1.3
    e.loc[m, "open"] *= 0.8
    e.loc[m, "volume"] *= 5
    return e


_CALLS = {
    "cvi": lambda f, d: f(d["high"], d["low"]),
    "bw_mfi": lambda f, d: f(d["high"], d["low"], d["close"], d["volume"]),
    "smc_sweep": lambda f, d: f(d["open"], d["high"], d["low"], d["close"]),
}


def _sweep(name, fn, d):
    """(count of J at which output before J moved, worst |delta| seen)."""
    call = _CALLS[name]
    base = np.asarray(call(fn, d), dtype=float)
    caught, worst = 0, 0.0
    for J in _J_SWEEP:
        b = np.asarray(call(fn, _perturb(d, J)), dtype=float)[:J]
        a = base[:J]
        m = np.isfinite(a) & np.isfinite(b)
        if not m.any():
            continue
        delta = float(np.abs(a[m] - b[m]).max())
        if delta > 0:
            caught += 1
            worst = max(worst, delta)
    return caught, worst


def test_cvi_is_causal_and_its_backdating_mutant_is_caught():
    d = _frame()
    real, _ = _sweep("cvi", ta.cvi, d)
    assert real == 0, f"cvi leaks the future at {real} of {len(_J_SWEEP)} J values"
    mut = _mutate("pandas_ta.volatility.cvi",
                  "prior = ema_hl.shift(roc_length)",
                  "prior = ema_hl.shift(-roc_length)")
    caught, worst = _sweep("cvi", mut, d)
    assert caught == len(_J_SWEEP), \
        f"the mutant escaped at {len(_J_SWEEP) - caught} J values"
    assert worst > 1.0


def test_bw_mfi_is_causal_and_its_backdating_mutant_is_caught():
    d = _frame()
    real, _ = _sweep("bw_mfi", ta.bw_mfi, d)
    assert real == 0, f"bw_mfi leaks the future at {real} of {len(_J_SWEEP)} J values"
    mut = _mutate("pandas_ta.volume.bw_mfi",
                  "avg_volume = sma(volume, length=length)",
                  "avg_volume = volume.rolling(length, center=True).mean()")
    caught, worst = _sweep("bw_mfi", mut, d)
    assert caught == len(_J_SWEEP), \
        f"the mutant escaped at {len(_J_SWEEP) - caught} J values"
    assert worst > 0.0


def test_smc_sweep_is_causal_and_ONE_J_would_not_have_caught_its_mutant():
    """The whole reason Gate B here is a SWEEP and not a value.

    Measured: the back-dating mutant surfaces at 87 of 775 J values -- 11.2% --
    and is invisible at J = 100, 150, 200, 250, 500, 600 and 700. The real
    module leaks at 0 of 775.
    """
    d = _frame()
    events = int((ta.smc_sweep(d["open"], d["high"], d["low"], d["close"]) != 0).sum())
    assert events > 50, f"only {events} events -- the frame cannot test anything"

    real, _ = _sweep("smc_sweep", ta.smc_sweep, d)
    assert real == 0, f"smc_sweep leaks the future at {real} of {len(_J_SWEEP)} J"

    mut = _mutate(
        "pandas_ta.trend.smc_sweep",
        "    smc_sweep = Series(bull_sweep + bear_sweep, index=close.index)",
        "    smc_sweep = Series(bull_sweep + bear_sweep, index=close.index).shift(-1)")
    caught, _ = _sweep("smc_sweep", mut, d)
    assert caught > 0, "the back-dating mutant was NOT caught at ANY J"
    # and the finding itself: a single J is not enough
    assert caught < len(_J_SWEEP) // 2, (
        "the mutant is now caught at more than half of all J -- if that is a "
        "real improvement, update the 87/775 figure in this docstring; if it "
        "is a weakened mutant, do not accept it")
    single = {J: _sweep_at(mut, d, J) for J in (100, 150, 200, 250, 500, 600, 700)}
    assert not any(single.values()), (
        "one of the round-number J values now catches the mutant; the "
        "measured escape set has changed and the docstring is stale: " + str(single))


def _sweep_at(fn, d, J):
    call = _CALLS["smc_sweep"]
    a = np.asarray(call(fn, d), dtype=float)[:J]
    b = np.asarray(call(fn, _perturb(d, J)), dtype=float)[:J]
    m = np.isfinite(a) & np.isfinite(b)
    return bool(m.any() and float(np.abs(a[m] - b[m]).max()) > 0)


def test_the_degenerate_smc_mutant_is_degenerate():
    """The mutant that LOOKS right and certifies nothing.

    Back-dating the SWING LOOKUP instead of the write makes the rolling window
    contain the bar it is compared against, so `low < swing_low` is
    arithmetically impossible and the mutant is a CONSTANT ZERO. A constant
    cannot leak, so it scores 0 at every J and reads as "causal". Pinned so
    nobody swaps the working mutant for this one.
    """
    d = _frame()
    # BOTH lookups. An earlier version patched only `swing_low` and asserted a
    # constant zero -- but `bear_sweep` reads `swing_high`, which that mutation
    # leaves alone, so the bear branch kept firing (28 events on this fixture)
    # and the test failed against its own stated premise. The degeneracy is real
    # and is per-branch: patch one side and you get a HALF-degenerate mutant,
    # which is worse than either, because it still looks like it detects
    # something.
    mut = _mutate(
        "pandas_ta.trend.smc_sweep",
        ("swing_low = low.rolling(window=length).min().shift(1)",
         "swing_high = high.rolling(window=length).max().shift(1)"),
        ("swing_low = low.rolling(window=length).min().shift(-1)",
         "swing_high = high.rolling(window=length).max().shift(-1)"))
    out = mut(d["open"], d["high"], d["low"], d["close"])
    assert int((out != 0).sum()) == 0, (
        "this mutant is no longer degenerate -- re-check whether it is now a "
        "usable causality mutant")
    caught, _ = _sweep("smc_sweep",
                       lambda o, h, l, c, **k: mut(o, h, l, c, **k), d)
    assert caught == 0, "a constant column cannot leak; something else changed"


# --------------------------------------------------------------- Gate D

@pytest.mark.parametrize("mult", [8, 64])
def test_gate_d_is_bit_identical_not_a_tolerance(mult):
    """`== 0.0`. ALTPORT-1 measured MFI_BW_SF FAILING this at 0.004193 on tti's
    ROUNDED output; the fork does not round, and the failure does not
    transfer."""
    d = _frame()
    base = _columns(d)
    sd = d.copy()
    sd[["open", "high", "low", "close"]] *= mult
    scaled = _columns(sd)
    for name in SHIPPED_COLUMNS:
        a = base[name].to_numpy(float)
        b = scaled[name].to_numpy(float)
        fa, fb = np.isfinite(a), np.isfinite(b)
        assert (fa == fb).all(), f"{name}: NaN masks differ at x{mult}"
        m = fa & fb
        assert m.sum() > 700
        assert float(np.abs(a[m] - b[m]).max()) == 0.0, \
            f"{name} is not bit-identical at x{mult}"
        assert 0 < int((a[m] != 0).sum()) < int(m.sum()) + 1


def test_mfi_bw_sf_is_also_invariant_under_volume_scaling():
    """The reason it ships as a DOUBLE ratio: Bill Williams' raw index is TL
    per share and doubles when the share count halves."""
    d = _frame()
    base = ta.bw_mfi(d["high"], d["low"], d["close"], d["volume"]).to_numpy(float)
    sd = d.copy()
    sd["volume"] = sd["volume"] * 8
    scaled = ta.bw_mfi(sd["high"], sd["low"], sd["close"], sd["volume"]).to_numpy(float)
    m = np.isfinite(base) & np.isfinite(scaled)
    assert m.sum() > 700
    assert float(np.abs(base[m] - scaled[m]).max()) == 0.0
    raw = ta.bw_mfi(d["high"], d["low"], d["close"], d["volume"], raw=True).to_numpy(float)
    raw8 = ta.bw_mfi(sd["high"], sd["low"], sd["close"], sd["volume"], raw=True).to_numpy(float)
    mm = np.isfinite(raw) & np.isfinite(raw8)
    assert float(np.abs(raw[mm] - raw8[mm]).max()) > 0.0, \
        "the RAW form is supposed to fail scale-freedom -- that is why it is unregistered"


# --------------------------------------------------------------- Gate C

@_needs_cache
def test_gate_c_every_column_fires_on_real_data():
    """Counts, not adjectives. 578 files in the cache, 92 usable, 422,136 bars."""
    n_files, frames = _real_frames()
    assert n_files >= 500, f"only {n_files} parquet files -- cache looks wrong"
    assert len(frames) >= 80, f"only {len(frames)} usable frames"
    bars = sum(len(d) for _, d in frames)
    assert bars > 300_000, bars
    fires = {c: 0 for c in SHIPPED_COLUMNS}
    nonzero = {c: 0 for c in SHIPPED_COLUMNS}
    for _, d in frames:
        for name, s in _columns(d).items():
            a = s.to_numpy(float)
            nz = int((np.isfinite(a) & (a != 0)).sum())
            nonzero[name] += nz
            fires[name] += 1 if nz else 0
    # MFI_BW_SF_20 fires on 91 of 92 -- see docstring item 6. >= 90 so a real
    # regression cannot hide behind that one frame.
    for name in SHIPPED_COLUMNS:
        assert fires[name] >= 90, f"{name} fires on only {fires[name]} frames"
        assert nonzero[name] > 5_000, f"{name} non-zero on only {nonzero[name]} bars"
    assert nonzero["SMC_SWEEP_15_1.5"] < bars * 0.05, \
        "a sparse event flag firing on 5%+ of bars is not a sweep any more"


@_needs_cache
def test_smc_sweep_is_signed_on_real_data():
    """The tied-zero trap. Measured: 2,547 `+1` and 4,605 `-1` of 422,136."""
    _, frames = _real_frames()
    pos = neg = 0
    for _, d in frames:
        s = ta.smc_sweep(d["open"], d["high"], d["low"], d["close"]).to_numpy(float)
        pos += int((s == 1).sum())
        neg += int((s == -1).sum())
    assert pos > 500 and neg > 500, (
        f"+1={pos} -1={neg}: an unsigned or one-sided flag correlates rho ~ 1 "
        "with any other column nonzero only on its own support")
    assert 0.1 < pos / neg < 10.0, f"pathologically lopsided: +1={pos} -1={neg}"


# --------------------------------------------------------------- Gate E

def test_the_gate_e_numbers_are_written_down_where_they_can_be_checked():
    """Gate E cannot run here -- it needs the parent engine's 492-column
    production output. What CAN be pinned is that the measured numbers reach
    the write-up, and that the reverted candidates stay in it."""
    doc = os.path.join(_FORK, "docs", "AltportPortsMeasured.md")
    assert os.path.isfile(doc), "docs/AltportPortsMeasured.md is missing"
    text = open(doc, encoding="utf8").read()
    for col, (rho, against, n) in GATE_E.items():
        assert col in text, f"{col} absent from the write-up"
        assert f"{rho:.6f}" in text, f"{col}'s measured rho {rho:.6f} absent"
        assert against in text, f"{col}'s adversary {against} absent"
        assert f"{n:,}" in text or str(n) in text, f"{col}'s sample size absent"
    for col, why in NOT_PORTED.items():
        assert col in text, (
            f"{col} was measured and dropped and must stay in the table: {why}")


# ---------------------------------------------------------- attribution

def test_every_ported_module_attributes_its_MIT_upstream():
    """Both sources are MIT: permissive, but attribution is still required."""
    want = {
        "pandas_ta/volatility/cvi.py": "pandas-ta-classic",
        "pandas_ta/trend/smc_sweep.py": "pandas-ta-classic",
        "pandas_ta/volume/bw_mfi.py": "trading-technical-indicators",
    }
    for rel, repo in want.items():
        src = open(os.path.join(_FORK, rel), encoding="utf8").read()
        assert "MIT" in src, f"{rel} does not name the upstream licence"
        assert repo in src, f"{rel} does not name the upstream repository"


def test_neither_upstream_repo_is_committed_into_this_one():
    """They live in `../AlternativeRepos/`, outside this repo's root."""
    for name in ("pandas-ta-classic", "pandas_ta_classic",
                 "trading-technical-indicators", "tti"):
        assert not os.path.exists(os.path.join(_FORK, name)), \
            f"{name} must not be vendored into this repository"


def test_no_shipped_module_imports_an_upstream_alternative_repo():
    """The fork's only consumer pip-installs it; neither upstream is a
    dependency, so a shipped module importing one would break the install."""
    offenders = []
    for root, _dirs, files in os.walk(os.path.join(_FORK, "pandas_ta")):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            src = open(p, encoding="utf8").read()
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import pandas_ta_classic", "from pandas_ta_classic",
                                 "import tti", "from tti")):
                    offenders.append(f"{os.path.relpath(p, _FORK)}: {s}")
    assert offenders == [], offenders
