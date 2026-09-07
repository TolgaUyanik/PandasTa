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

_broken_alias = sorted(v for v in ALIAS.values() if v not in SURFACE)
if _broken_alias:
    raise SystemExit(
        f"ALIAS maps to names the fork does not have: {_broken_alias}. An "
        f"alias is a claim of equivalence; an unresolvable one silently became "
        f"a `have` in the first version of this scanner."
    )


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


def call_fork(fork_name, frame, kwargs=None, length=None):
    """Call a fork function, honouring kwargs variants and two-series shapes."""
    fn = getattr(ta, fork_name, None)
    if fn is None:
        return NOT_CALLABLE
    params = inspect.signature(fn).parameters
    call = {}
    for pname in params:
        if pname in ("open", "open_", "high", "low", "close", "volume",
                     "source", "source_a"):
            column = {"open_": "open", "open": "open", "high": "high",
                      "low": "low", "close": "close", "volume": "volume",
                      "source": "close", "source_a": "close"}[pname]
            call[pname] = frame[column]
        elif pname in ("source_b", "close2", "other"):
            # A distinct second series, not a copy: correlation(x, x) is 1.
            call[pname] = frame["open"]
    if not call:
        return NOT_CALLABLE
    extra = dict(kwargs or {})
    if length is not None and "length" in params:
        extra["length"] = length
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            return fn(**call, **extra)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE


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


def classify(name, category):
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
                "kwargs plus the declared ALIAS_KWARGS variants). NOT a claim "
                "that no reachable parameterisation exists.")

    fork_file = _source_file(ta, fork_name)
    where = _rel(fork_file, FORK) if fork_file else f"Category[{category}]"

    cls_fn = getattr(tac, name, None)
    fork_fn = getattr(ta, fork_name, None)
    alias_kwargs = ALIAS_KWARGS.get(name)
    if cls_fn is None or fork_fn is None:
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                "not-compared",
                "name is registered but not resolvable as a module-level "
                "function on one side; NOT recorded as `have`")

    frame = _probe_frame()
    try:
        out_cls = _call(cls_fn, frame, name)
        out_fork = (call_fork(fork_name, frame, alias_kwargs)
                    if (alias_kwargs or fork_name in TWO_SERIES)
                    else _call(fork_fn, frame, fork_name))
        if out_fork is NOT_CALLABLE:
            out_fork = _call(fork_fn, frame, fork_name)
        if out_cls is NOT_CALLABLE and name in TWO_SERIES_CLS:
            out_cls = _call_two_series(cls_fn, frame)
    except Exception as exc:                                # noqa: BLE001
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                "not-compared",
                f"probe call raised ({type(exc).__name__}: "
                f"{str(exc)[:80]}); NOT recorded as `have`")

    outcome, detail = _same_output(out_cls, out_fork, frame)
    if outcome in ("identical", "warmup-offset"):
        # A pair identical on every overlapping value, differing only in how
        # many warm-up bars each side emits, is the SAME indicator. Filing that
        # as a porting candidate sent a reader to compare two identical
        # formulas -- `ULTOSC` vs `uo` differed by 7.1e-15 and one NaN.
        return ("have", fork_name, "yes",
                f"{where}:{_def_line(fork_file, fork_name)}",
                outcome, detail)
    if outcome in ("unknown", "not-callable", "degenerate", "shape"):
        return ("unknown - not comparable", fork_name, "no", f"{where}:1",
                outcome, detail + "; NOT recorded as `have`")

    if name in ALIAS:
        return ("port - alternate impl", fork_name, "yes", f"{where}:1",
                "divergent",
                f"cross-name match ({name} -> {fork_name}) but {detail}")
    return ("port - alternate impl", fork_name, "yes", f"{where}:1",
            "divergent",
            f"same name, different behaviour: {detail}. Shared ancestry means "
            f"one side may carry a fix the other lacks -- PTCLASSIC-1 resolves "
            f"which.")


def _fork_outputs(frame):
    """Every fork indicator's output on the probe frame, computed once."""
    out = {}
    for name in sorted(SURFACE):
        fn = getattr(ta, name, None)
        if fn is None or not callable(fn):
            continue
        try:
            value = _call(fn, frame, name)
        except Exception:                                   # noqa: BLE001
            continue
        if value is NOT_CALLABLE or value is None:
            continue
        out[name] = value
    return out


def find_equivalent(cls_name, frame, fork_cache):
    """Search the whole fork surface for a numerical match to `cls_name`.

    `port` asserts absence. Asserting absence by name alone is what put
    `medprice`, `typprice` and `avgprice` in the gap list when the fork ships
    all three as `hl2`, `hlc3` and `ohlc4`.
    """
    fn = getattr(tac, cls_name, None)
    if fn is None:
        return None, ""
    try:
        mine = _call(fn, frame, cls_name)
    except Exception:                                       # noqa: BLE001
        return None, ""
    if mine is NOT_CALLABLE or mine is None:
        return None, ""

    for fork_name, theirs in fork_cache.items():
        outcome, detail = _same_output(mine, theirs, frame)
        if outcome == "identical":
            return fork_name, detail
    return None, ""


def _environment_stamp():
    """What the verdicts below are conditional on.

    Installing TA-Lib moved `dm` from `port - alternate impl` to `have`: both
    packages defer to TA-Lib when it is importable, so their outputs converge.
    A verdict column is therefore a statement about THIS environment, and a
    regeneration elsewhere can legitimately differ. Recording it turns a silent
    reclassification into a visible one.
    """
    try:
        import talib
        have_talib = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        have_talib = "talib ABSENT"
    import pandas
    return f"{have_talib}; pandas {pandas.__version__}"


def main():
    rows = []
    frame = _probe_frame()
    fork_cache = _fork_outputs(frame)
    print(f"fork probe cache: {len(fork_cache)} indicators callable", flush=True)

    discovered = {}
    for category in sorted(tac.Category):
        for name in sorted(tac.Category[category]):
            verdict, equiv, audited, evidence, divergence, note = classify(
                name, category)

            # `port` is a claim of ABSENCE -- search before making it.
            if verdict == "port":
                match, detail = find_equivalent(name, frame, fork_cache)
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
