# -*- coding: utf-8 -*-
"""PTCLASSIC-0: classify every indicator `pandas-ta-classic` registers, against
what this fork actually ships.

Written to the ALTREPO contract (`TODO.md`): the classifier IS the artifact --
counts may drift with the upstream repo, VERDICTS may not. Re-running must
reproduce the verdict column, and `tests/test_altrepo_ptclassic_csv.py` asserts
that.

Two traps this repo has already paid for, both closed here mechanically rather
than by care:

1. **"Absent" must mean absent, not unmatched.** Diffing against the fork's
   `Category` alone reports `drawdown`, `hwma`, `ma` and `vp` as missing -- the
   fork HAS all four, outside `Category`. The reference set is therefore the
   full callable surface: `Category` + `df.ta` accessors + module-level
   functions (which includes the `_pine` primitives, so classic's `rolling_max`
   can meet the fork's `highest`).

2. **A name match is not an implementation match.** PINEBI-0 shipped five wrong
   `have` verdicts on exactly that axis (`dm`, `kcw`, `cagr`, `cross`,
   `crossunder`). Every shared name here is CALLED on a common synthetic OHLCV
   frame and the two outputs compared elementwise; only agreement is recorded
   as `have`.

   ⚠ The first version of this scanner compared ASTs instead, and flagged 152
   of 149 shared names as divergent -- i.e. carried no information. Hand-diffing
   `ao` and `cdl_inside` showed why: pandas-ta-classic has been modernised
   across the board (type annotations, `return` -> `return None`, added
   None-guards, refactored offset/fillna tails), so every body differs
   cosmetically while the maths is often identical. Comparing behaviour instead
   of text is both stronger and immune to that. The frame is seeded, so the
   verdict column stays reproducible.

   False `divergent` costs a read; false `have` deletes a real port silently, so
   where the comparison cannot run at all the row is recorded as `unknown`, never
   as `have`.

⚠ The task text's "302 modules / 288 / candles 66" are FILE counts. This scans
what the package REGISTERS: 224 indicators, of which candles is 5 -- the other
60 candle files are TA-Lib `CDL_*` wrappers reached through `cdl_pattern`.

⚠ Licence: pandas-ta-classic is MIT. Attribution is required on any port, and
the repo itself must NOT be committed into this one.

Usage:  python docs/gen_altrepo_pandas_ta_classic.py [out.csv]
"""
import ast
import csv
import inspect
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
CLASSIC = os.path.join(os.path.dirname(FORK), "AlternativeRepos",
                       "pandas-ta-classic")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(FORK), "AlternativeRepos", "altrepo_pandas_ta_classic.csv")

if not os.path.isdir(CLASSIC):
    sys.exit(f"pandas-ta-classic not found at {CLASSIC}")

sys.path.insert(0, CLASSIC)
sys.path.insert(0, FORK)
import pandas_ta as ta                                    # noqa: E402
import pandas_ta_classic as tac                           # noqa: E402
from pandas_ta.core import AnalysisIndicators as AI       # noqa: E402

sys.path.insert(0, HERE)
from _altrepo_resolve import (
    fork_surface_cache,                              # noqa: E402
    PINNED_LENGTH, call_fork, fork_signature_kind, probe_variants,
    validate_alias_targets,
)

# ---------------------------------------------------------------- the fork
CATEGORY = {n for v in ta.Category.values() for n in v}
ACCESSOR = {n for n, v in vars(AI).items()
            if not n.startswith("_") and inspect.isfunction(v)}
MODULE = {n for n, v in vars(ta).items()
          if not n.startswith("_") and inspect.isfunction(v)}
SURFACE = CATEGORY | ACCESSOR | MODULE

# Cross-name equivalents: classic's name -> the fork's name for the same thing.
# Every entry is a claim that must be justified in EVIDENCE below, and the
# guard test opens the cited file and checks the token is really there.
ALIAS = {
    "rolling_max": "highest",
    "rolling_min": "lowest",
    "rolling_sum": "cum",
}
# `npabs` was here mapped to a fork `abs` that DOES NOT EXIST. The classifier
# then reported it as `have`, with a note claiming it was "reachable as
# df.ta.abs()" -- a fabricated all-clear of precisely the kind this file's
# header warns about, produced by this file. An alias whose target is absent is
# now fatal rather than silently generous.

# One fork function can expose several alt-repo indicators behind kwargs.
# `linreg` alone covers linreg, slope, angle, intercept and tsf. Without this
# the scanner published three of them as absences while the TA-Lib scan, which
# HAD the machinery, published the same functions as `have`.
ALIAS_KWARGS = {
    "linregslope": {"slope": True},
    "linregangle": {"angle": True, "degrees": True},
    "linregintercept": {"intercept": True},
    "tsf": {"tsf": True},
}
ALIAS.update({
    "linregslope": "linreg", "linregangle": "linreg",
    "linregintercept": "linreg", "tsf": "linreg",
    "correl": "correlation",
    # `ta.dm` returns DMP_14/DMN_14 -- the same indicator, differently scaled
    # (measured 9.0 at length 14). `port` would send a reader to reimplement
    # Wilder DM from scratch; it is an alternate implementation.
    "plus_dm": "dm", "minus_dm": "dm",
})

# Two-series signatures the close-only probe could never build. `correlation`
# shipped as an absence in one CSV and as "the harness cannot call it" in the
# other; it is callable, and it matches at 0.0 / 7.8e-12.
TWO_SERIES = {"correlation"}
# alt-repo side equivalents of the same shape
TWO_SERIES_CLS = {"correl", "beta"}


def _call_two_series(fn, frame):
    """Feed a two-series alt-repo function close and open."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return fn(frame["close"], frame["open"], 30)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE

# `n/a` groups, with the reason recorded per row rather than assumed.
MATH_HELPERS = set(tac.Category.get("math", []))

EVIDENCE = {
    # classic name: (fork file, token the guard must find in it)
    "rolling_max": ("pandas_ta/utils/_pine.py", "def highest"),
    "rolling_min": ("pandas_ta/utils/_pine.py", "def lowest"),
    "rolling_sum": ("pandas_ta/utils/_pine.py", "def cum"),
}

validate_alias_targets(ALIAS, SURFACE, "gen_altrepo_pandas_ta_classic")


class _NotCallable:
    """Sentinel: the probe harness could not construct a call for this
    signature. NEVER conflated with a None return from the indicator."""

    def __repr__(self):
        return "NOT_CALLABLE"


NOT_CALLABLE = _NotCallable()


def _probe_frame(n=260, seed=7):
    """A seeded synthetic OHLCV frame. Seeded so the verdict column is
    reproducible -- the guard test re-runs this whole file and diffs it."""
    import numpy as np
    from pandas import DataFrame, date_range

    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    high = close + rng.uniform(0.1, 1.5, n)
    low = close - rng.uniform(0.1, 1.5, n)
    open_ = low + (high - low) * rng.uniform(0, 1, n)
    volume = rng.integers(1_000, 100_000, n).astype(float)
    return DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": volume},
        index=date_range("2020-01-01", periods=n, freq="D"))


# Parameter name -> which probe column to feed it. Beyond OHLCV because the
# fork's `_pine` primitives take `source`, and `long_run`/`short_run` take two
# series. Without these the harness silently fed nothing, returned None, and the
# row was filed `unknown` -- a limitation of the probe recorded as a property of
# the indicator.
_ARGS = {
    "open": "open", "open_": "open", "high": "high", "low": "low",
    "close": "close", "volume": "volume",
    "source": "close", "series": "close", "trend": "close",
}

# `fast`/`slow` name SERIES in the run functions and INTEGER LENGTHS everywhere
# else (`macd(close, fast=12, slow=26)`). Mapping them globally fed a Series
# into a length and raised "truth value of a Series is ambiguous" on 17 rows --
# every one of which was then filed `unknown`, i.e. a harness bug recorded as an
# unresolved property of the indicator. Same parameter name, different meaning;
# an allowlist is the only honest discriminator here.
_SERIES_PAIR_FNS = {"long_run", "short_run"}

# Functions whose first parameter is a NAME, not a series.
_NAME_ARG = {"ma": "sma"}


def _call(fn, frame, fn_name=""):
    """Call `fn` with whichever probe series its signature asks for.

    Returns the sentinel `NOT_CALLABLE` when the signature exposes no
    recognised series parameter, so "the harness could not drive this" stays
    distinguishable from "the indicator returned None".
    """
    import numpy as np

    kwargs = {}
    for pname in inspect.signature(fn).parameters:
        if pname in _NAME_ARG and not kwargs:
            kwargs[pname] = _NAME_ARG[pname]
            continue
        column = _ARGS.get(pname)
        if column is None and pname in ("fast", "slow")                 and fn_name in _SERIES_PAIR_FNS:
            column = {"fast": "close", "slow": "open"}[pname]
        if column is not None:
            kwargs[pname] = frame[column]
    if fn_name in _NAME_ARG:
        kwargs.setdefault("name", _NAME_ARG[fn_name])
    if not any(hasattr(v, "index") for v in kwargs.values()):
        return NOT_CALLABLE
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        np.seterr(all="ignore")
        return fn(**kwargs)


def _is_identity(values, frame):
    """Does this output just hand back one of its input columns?

    `edecay` and `highest` both return `close` unchanged at default parameters
    (`highest` resolves `length` to 1), so a naive comparison called them the
    same indicator. Agreement between two identity functions is agreement about
    the probe frame, not about the implementations.
    """
    import numpy as np

    if values is None or getattr(values, "ndim", 1) != 1:
        return None
    arr = np.asarray(values, dtype="float64")
    for column in frame.columns:
        col = frame[column].to_numpy(dtype="float64")
        if arr.shape != col.shape:
            continue
        mask = ~np.isnan(arr)
        if mask.sum() >= 3 and np.allclose(arr[mask], col[mask], rtol=1e-9):
            return column
    return None


def _columns_of(value):
    """Every 1-D series inside `value`, as {label: ndarray}."""
    import numpy as np
    from pandas import DataFrame, Series

    if isinstance(value, DataFrame):
        return {str(c): value[c].to_numpy(dtype="float64")
                for c in value.columns}
    if isinstance(value, Series):
        return {str(value.name): value.to_numpy(dtype="float64")}
    if isinstance(value, tuple):
        out = {}
        for i, part in enumerate(value):
            if part is None:
                continue
            out.update({f"t{i}:{k}": v for k, v in _columns_of(part).items()})
        return out
    try:
        arr = np.asarray(value, dtype="float64")
        if arr.ndim == 1:
            return {"?": arr}
    except Exception:                                       # noqa: BLE001
        pass
    return {}


def _agree(x, y, rtol=1e-9, atol=1e-12):
    """-> (verdict, detail) for two 1-D arrays, tolerant of warm-up extent.

    `np.allclose(equal_nan=True)` demands the NaN masks coincide, so two
    identical implementations that emit a different number of warm-up bars
    compare as different. `ULTOSC` vs `uo` failed on exactly that: max abs diff
    7.1e-15 with one extra NaN. The overlap is compared first; a NaN-extent
    difference is reported as its own, milder outcome.
    """
    import numpy as np

    if x.shape != y.shape:
        return "shape", f"shape {x.shape} vs {y.shape}"
    both = ~(np.isnan(x) | np.isnan(y))
    if both.sum() < 5:
        return "unknown", "fewer than 5 overlapping non-NaN values"
    if not np.allclose(x[both], y[both], rtol=rtol, atol=atol):
        worst = float(np.nanmax(np.abs(x[both] - y[both])))
        return "divergent", (f"max abs diff {worst:.6g} over {int(both.sum())} "
                             f"comparable values")
    nan_gap = int((np.isnan(x) ^ np.isnan(y)).sum())
    if nan_gap:
        # BOUNDED. Unbounded, this promoted a pair to `have` on as few as five
        # agreeing values with 250 bars of NaN on one side -- agreement on a
        # sliver is not agreement. The overlap must be most of the series and
        # the warm-up difference must be small.
        n = len(x)
        if nan_gap > max(2, 0.05 * n) or both.sum() < 0.5 * n:
            return "divergent", (
                f"agree on their {int(both.sum())} overlapping values but the "
                f"warm-up extents differ by {nan_gap} of {n} bars -- too much "
                f"to call the same series")
        return "warmup-offset", (
            f"identical on all {int(both.sum())} of {n} overlapping values; the "
            f"two differ only in warm-up extent ({nan_gap} bar(s) NaN on one "
            f"side only)")
    return "identical", f"agree on all {int(both.sum())} values"


def _same_output(a, b, frame=None):
    """-> (verdict_word, detail). Shape-, NaN- and COLUMN-aware.

    Compares every column of one side against every column of the other, so a
    multi-column return is not written off on `type(a) is not type(b)`. That
    shortcut previously produced 28 rows across the two scanners stamped
    `audited=yes` with no numeric comparison behind them.
    """
    import numpy as np

    if a is NOT_CALLABLE or b is NOT_CALLABLE:
        return ("not-callable",
                "the probe harness has no call for this signature -- a "
                "limitation of this scanner, NOT a property of the indicator")
    if a is None or b is None:
        return ("unknown", "one side returned None on the probe frame")

    left, right = _columns_of(a), _columns_of(b)
    if not left or not right:
        return ("unknown", "output not resolvable to numeric columns")

    best = None
    for lname, lv in left.items():
        for rname, rv in right.items():
            verdict, detail = _agree(lv, rv)
            rank = {"identical": 0, "warmup-offset": 1, "divergent": 2,
                    "shape": 3, "unknown": 4}[verdict]
            if best is None or rank < best[0]:
                best = (rank, verdict, detail, lname, rname)
            if rank == 0:
                break
        if best and best[0] == 0:
            break

    rank, verdict, detail, lname, rname = best
    where = ("" if len(left) == 1 and len(right) == 1
             else f" [matched column {lname!r} against {rname!r}; "
                  f"{len(left)} vs {len(right)} column(s)]")

    if verdict in ("identical", "warmup-offset") and frame is not None:
        arr = left[lname]
        for column in frame.columns:
            col = frame[column].to_numpy(dtype="float64")
            if arr.shape != col.shape:
                continue
            mask = ~np.isnan(arr)
            if mask.sum() >= 3 and np.allclose(arr[mask], col[mask], rtol=1e-9):
                return ("degenerate",
                        f"both sides return the input `{column}` unchanged at "
                        f"default parameters -- agreement here is about the "
                        f"probe frame, not the implementations")
        finite = arr[~np.isnan(arr)]
        if finite.size and np.ptp(finite) == 0:
            return ("degenerate",
                    f"both sides return the constant {finite[0]:.6g} on the "
                    f"probe frame -- agreement here is not evidence")

    return (verdict, detail + where)


def _source_file(module_obj, name):
    fn = getattr(module_obj, name, None)
    if fn is None:
        return None
    try:
        return inspect.getsourcefile(fn)
    except TypeError:
        return None


def _def_line(path, name):
    """1-based line of `def <name>` in `path`, or 1 if not found.

    A receipt citing `:1` is a receipt of nothing. PINEBI-0 already shipped a
    guard that checked evidence FORMAT without opening the file; the companion
    test here reads this line and asserts the def is really on it.
    """
    try:
        for i, line in enumerate(io.open(path, encoding="utf8"), 1):
            if line.lstrip().startswith(f"def {name}("):
                return i
    except OSError:
        pass
    return 1


def _rel(path, root):
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except (ValueError, TypeError):
        return path


def classify(name, category, frame):
    """-> (verdict, equivalent, audited, evidence, divergence, note)

    Pure enough to test: it consults only the module-level sets above and the
    two source trees, never the CSV it is about to write.
    """
    if name in MATH_HELPERS and name not in SURFACE and name not in ALIAS:
        return ("n/a - arithmetic helper, not a feature", "", "n/a", "", "",
                "classic's `math/` group wraps numpy/TA-Lib scalar maths "
                "(sin, add, floor). Not indicators; nothing to port.")

    fork_name = name if name in SURFACE else ALIAS.get(name)
    if fork_name is None:
        return ("port", "", "n/a", "", "",
                "no fork function of this NAME, and no cross-name equivalent "
                "found by the output search over the fork surface (default "
                "kwargs plus the declared ALIAS_KWARGS variants, each swept at "
                "length 1/5/14/30 and with the primary series overridden to "
                "volume). NOT a claim that no reachable parameterisation "
                "exists.{near_miss}")

    fork_file = _source_file(ta, fork_name)
    where = _rel(fork_file, FORK) if fork_file else f"Category[{category}]"

    cls_fn = getattr(tac, name, None)
    fork_fn = getattr(ta, fork_name, None)
    fork_file = _source_file(ta, fork_name)
    where = _rel(fork_file, FORK) if fork_file else f"Category[{category}]"

    if cls_fn is None or fork_fn is None:
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                "not-compared",
                "name is registered but not resolvable as a module-level "
                "function on one side; NOT recorded as `have`")

    # The alt-repo side. `correl`/`beta` take two series and the close-only
    # probe could never build the call -- which is how `correl` shipped as
    # "the harness cannot call it" while the answer was `have` at 0.0.
    try:
        out_cls = _call(cls_fn, frame, name)
    except Exception:                                       # noqa: BLE001
        out_cls = None
    if out_cls is NOT_CALLABLE or out_cls is None:
        out_cls = call_fork(cls_fn, frame)
    if out_cls is None or out_cls is NOT_CALLABLE:
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                "not-compared",
                f"the alt-repo function could not be driven on the probe frame "
                f"(signature kind: {fork_signature_kind(cls_fn)})")

    # EVERY declared way of calling the fork side, not just the default.
    variants = [ALIAS_KWARGS[name]] if name in ALIAS_KWARGS else []
    attempts = probe_variants(fork_fn, frame, kwargs_variants=variants,
                              fork_name=fork_name)
    if not attempts:
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                "not-compared",
                f"the probe harness has no call for `{fork_name}` "
                f"(signature kind: {fork_signature_kind(fork_fn)}); the pair "
                f"was never compared. NOT an absence.")

    # Sweep BOTH sides. Sweeping only the fork side left the alt-repo call at
    # its own default window, so `correl` (classic default 30 vs a fork call at
    # 14) read divergent when the two agree exactly at a matched length.
    cls_attempts = probe_variants(cls_fn, frame) or [("default", out_cls)]

    best = None
    for (cls_label, out_cls_v) in cls_attempts:
      for label, out_fork in attempts:
        outcome, detail = _same_output(out_cls_v, out_fork, frame)
        label = f"{label} vs classic {cls_label}"
        rank = {"identical": 0, "warmup-offset": 1, "divergent": 2,
                "shape": 3, "degenerate": 4, "unknown": 5,
                "not-callable": 6}.get(outcome, 7)
        if best is None or rank < best[0]:
            best = (rank, outcome, detail, label)
        if rank == 0:
            break
      if best and best[0] == 0:
          break
    _, outcome, detail, label = best
    line = _def_line(fork_file, fork_name) if fork_file else 1

    if outcome in ("identical", "warmup-offset"):
        return ("have", fork_name, "yes", f"{where}:{line}", outcome,
                f"{detail} [resolved with {label}]")
    if outcome in ("unknown", "not-callable", "degenerate", "shape"):
        return ("unknown - not comparable", fork_name, "no", f"{where}:{line}",
                outcome, detail + "; NOT recorded as `have`")

    if name in ALIAS:
        return ("port - alternate impl", fork_name, "yes", f"{where}:{line}",
                "divergent",
                f"cross-name match ({name} -> {fork_name}); best of "
                f"{len(attempts)} probed variants was {label}: {detail}")
    return ("port - alternate impl", fork_name, "yes", f"{where}:{line}",
            "divergent",
            f"same name, different behaviour across all {len(attempts)} probed "
            f"variants (best {label}): {detail}. Shared ancestry means one side "
            f"may carry a fix the other lacks -- PTCLASSIC-1 resolves which.")


def _environment_stamp():
    """What the verdicts are conditional on. Installing TA-Lib moved `dm`."""
    try:
        import talib
        have = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        have = "talib ABSENT"
    import pandas
    return f"{have}; pandas {pandas.__version__}"


def _fork_outputs(frame):
    """Delegates to the ONE shared surface cache (`_altrepo_resolve`).

    This was a private reimplementation -- one of three, each with its own
    series map and its own idea of which parameter is the window.
    """
    return fork_surface_cache(frame, SURFACE, ta)


def _related_to(mine, fork_cache, frame):
    """The closest NON-identical relative on the fork surface, or (None, "").

    An affine or monotone twin is an alternate implementation, not an absence.
    `emv` vs `eom` differ by a divisor and a smoothing; `fosc` vs `cfo` by
    TA-Lib dispatch; `rocr` vs `roc` by `100*(x-1)`. Each was published as
    "genuinely absent".
    """
    import numpy as np
    from scipy.stats import spearmanr

    def flat(value):
        try:
            arr = np.asarray(value, dtype="float64")
        except Exception:                                   # noqa: BLE001
            return None
        if arr.ndim == 2:
            arr = arr[:, 0]
        return arr if arr.ndim == 1 else None

    a = flat(mine)
    if a is None:
        return None, ""
    best = (0.0, None, "")
    for fork_name, values in fork_cache.items():
        for theirs in (values if isinstance(values, list) else [values]):
            b = flat(theirs)
            if b is None or b.shape != a.shape:
                continue
            mask = ~(np.isnan(a) | np.isnan(b))
            if mask.sum() < 40:
                continue
            x, y = a[mask], b[mask]
            if np.ptp(x) == 0 or np.ptp(y) == 0:
                continue
            rho = spearmanr(x, y).statistic
            if np.isnan(rho):
                continue
            if abs(rho) > abs(best[0]):
                # affine? fit y = m*x + c and report the residual
                m, c = np.polyfit(x, y, 1)
                resid = float(np.max(np.abs(y - (m * x + c))))
                scale = max(float(np.max(np.abs(y))), 1.0)
                best = (rho, fork_name,
                        f"Spearman {rho:+.6f}; affine fit y={m:.4g}x{c:+.4g} "
                        f"leaves max residual {resid:.3g} "
                        f"({resid / scale:.2e} relative)")
    if best[1] is not None and abs(best[0]) >= 0.99:
        return best[1], best[2]
    if best[1] is not None and abs(best[0]) >= 0.90:
        # A near-miss is NOT an equivalence, but it is not "nothing" either.
        # `fosc` sits at +0.950818 against `cfo` at every length and scalar
        # tried -- same family, genuinely different maths (TSF vs linreg).
        # Publishing that as "no cross-name equivalent found" invites the next
        # reviewer to read the two docstrings and call it a false gap, which is
        # exactly what happened. Name the near-miss and the number.
        return None, f"NEAR-MISS {best[1]}: {best[2]}"
    return None, ""


def find_equivalent(cls_name, frame, fork_cache):
    """Search the whole fork surface for a numerical match to `cls_name`.

    `port` asserts absence. Asserting absence by name alone is what put
    `medprice`, `typprice` and `avgprice` in the gap list while the fork ships
    them as `hl2`, `hlc3` and `ohlc4`.
    """
    fn = getattr(tac, cls_name, None)
    if fn is None:
        return None, ""
    # BOTH sides swept. Sweeping only the fork side left the alt-repo call at
    # its own default window, and that is why `stochf` (classic default
    # fastk=5) never met `ta.stoch(k=14, smooth_k=1)` -- false gap #10.
    mine_variants = probe_variants(fn, frame)
    if not mine_variants:
        single = _call(fn, frame, cls_name)
        if single is NOT_CALLABLE or single is None:
            return None, ""
        mine_variants = [("default", single)]

    for _label, mine in mine_variants:
        for fork_name, values in fork_cache.items():
            for theirs in values:
                outcome, detail = _same_output(mine, theirs, frame)
                if outcome in ("identical", "warmup-offset"):
                    return fork_name, detail
    return None, ""


def main():
    rows = []
    frame = _probe_frame()
    fork_cache = _fork_outputs(frame)
    print(f"fork probe cache: {len(fork_cache)} indicators callable", flush=True)

    discovered = {}
    related = {}
    near_miss = {}
    for category in sorted(tac.Category):
        for name in sorted(tac.Category[category]):
            verdict, equiv, audited, evidence, divergence, note = classify(
                name, category, frame)

            # `port` is a claim of ABSENCE -- search before making it.
            if verdict == "port":
                match, detail = find_equivalent(name, frame, fork_cache)
                if not match:
                    # Nothing reproduces it exactly -- but is anything on the
                    # surface an affine/monotone twin? `rocr`/`rocr100` are
                    # `100*(x-1)` relabellings of `roc` and shipped as absent
                    # because this branch did not exist. `fosc` is NOT: it
                    # peaks at +0.950818 against `cfo`, below the bar, and is
                    # reported as a near-miss rather than promoted.
                    fn = getattr(tac, name, None)
                    probe = _call(fn, frame, name) if fn is not None else None
                    if probe is NOT_CALLABLE or probe is None:
                        probe = call_fork(fn, frame) if fn is not None else None
                    if probe is not None and probe is not NOT_CALLABLE:
                        rel, why = _related_to(probe, fork_cache, frame)
                        if rel:
                            related[name] = (rel, why)
                        elif why:
                            near_miss[name] = why
                if match:
                    discovered[name] = match
                    verdict = "have"
                    equiv, audited, divergence = match, "yes", "identical"
                    fork_file = _source_file(ta, match)
                    evidence = (
                        f"{_rel(fork_file, FORK)}:"
                        f"{_def_line(fork_file, match)}" if fork_file else "")
                    note = (f"CROSS-NAME match found by search, not by name: "
                            f"classic `{name}` == fork `{match}`. {detail}")

            if "{near_miss}" in note:
                extra = near_miss.get(name, "")
                note = note.replace(
                    "{near_miss}", f" Nearest relative on the surface -- "
                                   f"{extra} -- close but NOT equivalent."
                    if extra else " Nothing on the fork surface correlates "
                                  "above 0.90 with it either.")

            if name in related:
                rel, why = related[name]
                fork_file = _source_file(ta, rel)
                verdict = "port - alternate impl"
                equiv, audited, divergence = rel, "yes", "related"
                evidence = (f"{_rel(fork_file, FORK)}:"
                            f"{_def_line(fork_file, rel)}" if fork_file else "")
                note = (f"NOT bit-identical, but an affine/monotone twin of the "
                        f"fork's `{rel}` -- {why}. Published as `port` "
                        f"(\"genuinely absent\") until the relation search "
                        f"existed.")

            rows.append({
                "name": name,
                "category": category,
                "verdict": verdict,
                "pandas_ta_equivalent": equiv,
                "audited": audited,
                "audit_evidence": evidence,
                "divergence": divergence,
                "note": note,
            })

    env = _environment_stamp()
    for r in rows:
        r["probe_env"] = env
    fields = ["name", "category", "verdict", "pandas_ta_equivalent", "audited",
              "audit_evidence", "divergence", "note", "probe_env"]
    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    if discovered:
        print(f"\ncross-name equivalents found by SEARCH ({len(discovered)}) "
              f"-- each would have been a false `port`:", flush=True)
        for a, b in sorted(discovered.items()):
            print(f"    classic {a:16} == fork {b}", flush=True)

    from collections import Counter
    split = Counter(r["verdict"] for r in rows)
    div = Counter(r["divergence"] for r in rows if r["divergence"])
    print(f"wrote {OUT}  ({len(rows)} rows)")
    print(f"fork surface: Category {len(CATEGORY)} | accessor "
          f"{len(CATEGORY | ACCESSOR)} | +module {len(SURFACE)}")
    for verdict, n in split.most_common():
        print(f"  {verdict:45} {n:4}")
    print("  divergence:", dict(div))


if __name__ == "__main__":
    main()
